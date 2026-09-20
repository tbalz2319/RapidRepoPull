"""Running ``git`` concurrently over a list of repositories.

The work is I/O bound -- almost all of it is spent waiting on the network -- so
it runs on a :class:`~concurrent.futures.ThreadPoolExecutor` sized for
concurrency rather than for CPU cores.
"""

from __future__ import annotations

import contextlib
import enum
import os
import shutil
import subprocess
import threading
import time
from collections.abc import Sequence
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from rapidrepopull.repolist import Repo

#: Plenty of parallelism for network-bound work without melting the remote.
DEFAULT_WORKERS = 16
#: Hard ceiling; beyond this git and the remote are the bottleneck anyway.
MAX_WORKERS = 64
DEFAULT_TIMEOUT = 600
DEFAULT_RETRIES = 2

#: Substrings that mark a failure as worth retrying.
_TRANSIENT_MARKERS = (
    "could not resolve host",
    "connection timed out",
    "connection reset",
    "operation timed out",
    "unable to access",
    "early eof",
    "rpc failed",
    "the remote end hung up",
    "ssl_error",
    "tls connection",
    "failed to connect",
    "temporary failure",
    "502 bad gateway",
    "503 service unavailable",
    "server error",
)


class GitNotFound(RuntimeError):
    """Raised when no usable ``git`` executable is on ``PATH``."""


class Status(enum.Enum):
    """Outcome of processing a single repository."""

    CLONED = "cloned"
    UPDATED = "updated"
    SKIPPED = "skipped"
    FAILED = "failed"

    @property
    def ok(self) -> bool:
        return self is not Status.FAILED


@dataclass
class Result:
    """What happened to one repository."""

    repo: Repo
    status: Status
    detail: str = ""
    attempts: int = 1
    duration: float = 0.0
    path: Path | None = None

    @property
    def ok(self) -> bool:
        return self.status.ok


@dataclass
class Summary:
    """Aggregate outcome of a run."""

    results: list[Result] = field(default_factory=list)
    interrupted: bool = False

    def of(self, status: Status) -> list[Result]:
        return [r for r in self.results if r.status is status]

    @property
    def failures(self) -> list[Result]:
        return self.of(Status.FAILED)

    @property
    def exit_code(self) -> int:
        if self.interrupted:
            return 130
        return 1 if self.failures else 0


def find_git() -> str:
    """Locate the ``git`` executable.

    The old version hardcoded ``/usr/bin/git``, which is simply wrong on macOS
    with Homebrew, on NixOS, and inside most slim containers.
    """
    git = os.environ.get("RRP_GIT_BINARY") or shutil.which("git")
    if not git:
        raise GitNotFound(
            "git was not found on PATH. Install it (e.g. 'apt install git', "
            "'brew install git') or set RRP_GIT_BINARY to its full path."
        )
    return git


def _git_env() -> dict:
    """Environment that keeps git strictly non-interactive.

    Without this, a private or renamed repository makes git block forever on a
    username prompt -- with a pool of threads all waiting, the run just hangs.
    """
    env = os.environ.copy()
    env.update(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "echo",
            "SSH_ASKPASS": "echo",
            "GCM_INTERACTIVE": "never",
            "GIT_CONFIG_NOSYSTEM": "1" if env.get("RRP_ISOLATED_GIT") else "0",
        }
    )
    env.pop("GIT_DIR", None)
    return env


def _is_transient(message: str) -> bool:
    lowered = message.lower()
    return any(marker in lowered for marker in _TRANSIENT_MARKERS)


def _run_git(
    args: Sequence[str],
    *,
    git: str,
    cwd: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [git, *args],
        cwd=str(cwd) if cwd else None,
        env=_git_env(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _message(proc: subprocess.CompletedProcess) -> str:
    """Condense git's output into a single readable line."""
    raw = (proc.stderr or proc.stdout or "").strip()
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    # git prefixes the interesting part with 'fatal:' or 'error:' when it fails.
    for line in reversed(lines):
        if line.lower().startswith(("fatal:", "error:")):
            return line
    return lines[-1] if lines else f"git exited with status {proc.returncode}"


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def _clone(repo: Repo, dest: Path, *, git: str, ssh: bool, depth: int | None, timeout: int):
    args = ["clone", "--quiet"]
    if depth:
        args += ["--depth", str(depth)]
    args += [repo.url(ssh=ssh), str(dest)]
    return _run_git(args, git=git, timeout=timeout)


def _update(dest: Path, *, git: str, depth: int | None, timeout: int):
    args = ["pull", "--quiet", "--ff-only"]
    if depth:
        args += ["--depth", str(depth)]
    return _run_git(args, git=git, cwd=dest, timeout=timeout)


def process_repo(
    repo: Repo,
    *,
    git: str,
    output_dir: Path,
    ssh: bool = False,
    depth: int | None = None,
    update: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    cancel: threading.Event | None = None,
) -> Result:
    """Clone ``repo`` into ``output_dir``, or update it if it is already there."""
    dest = output_dir / repo.name
    started = time.monotonic()

    def finish(status: Status, detail: str = "", attempts: int = 1) -> Result:
        return Result(
            repo=repo,
            status=status,
            detail=detail,
            attempts=attempts,
            duration=time.monotonic() - started,
            path=dest if status.ok else None,
        )

    if cancel is not None and cancel.is_set():
        return finish(Status.SKIPPED, "cancelled")

    if dest.exists():
        if not _is_git_repo(dest):
            return finish(Status.FAILED, f"{dest} exists and is not a git repository")
        if not update:
            return finish(Status.SKIPPED, "already present")
        try:
            proc = _update(dest, git=git, depth=depth, timeout=timeout)
        except subprocess.TimeoutExpired:
            return finish(Status.FAILED, f"update timed out after {timeout}s")
        if proc.returncode == 0:
            return finish(Status.UPDATED, "up to date")
        return finish(Status.FAILED, _message(proc))

    last_error = ""
    attempts_allowed = max(0, retries) + 1
    for attempt in range(1, attempts_allowed + 1):
        if cancel is not None and cancel.is_set():
            return finish(Status.SKIPPED, "cancelled", attempts=attempt)
        try:
            proc = _clone(repo, dest, git=git, ssh=ssh, depth=depth, timeout=timeout)
        except subprocess.TimeoutExpired:
            last_error = f"clone timed out after {timeout}s"
        else:
            if proc.returncode == 0:
                return finish(Status.CLONED, attempts=attempt)
            last_error = _message(proc)
            # A partial clone left behind would be mistaken for a real repo later.
            if dest.exists() and not _is_git_repo(dest):
                shutil.rmtree(dest, ignore_errors=True)
            if not _is_transient(last_error):
                return finish(Status.FAILED, last_error, attempts=attempt)

        if attempt < attempts_allowed:
            time.sleep(min(2 ** (attempt - 1), 8))

    return finish(Status.FAILED, last_error, attempts=attempts_allowed)


def clone_all(
    repos: Sequence[Repo],
    *,
    output_dir: Path,
    workers: int = DEFAULT_WORKERS,
    ssh: bool = False,
    depth: int | None = None,
    update: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    on_result: Callable[[Result], None] | None = None,
) -> Summary:
    """Process every repository concurrently and collect the outcomes.

    ``Ctrl-C`` stops new work from starting and lets in-flight clones finish,
    rather than leaving half-written directories behind.
    """
    summary = Summary()
    if not repos:
        return summary

    git = find_git()
    output_dir.mkdir(parents=True, exist_ok=True)
    workers = max(1, min(workers, MAX_WORKERS, len(repos)))
    cancel = threading.Event()

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="rrp") as pool:
        futures = {
            pool.submit(
                process_repo,
                repo,
                git=git,
                output_dir=output_dir,
                ssh=ssh,
                depth=depth,
                update=update,
                timeout=timeout,
                retries=retries,
                cancel=cancel,
            ): repo
            for repo in repos
        }
        pending = set(futures)
        try:
            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    result = future.result()
                    summary.results.append(result)
                    if on_result is not None:
                        on_result(result)
        except KeyboardInterrupt:
            summary.interrupted = True
            cancel.set()
            for future in pending:
                future.cancel()
            for future in pending:
                if not future.cancelled():
                    with contextlib.suppress(Exception):
                        summary.results.append(future.result())

    return summary
