"""Best-effort setup of cloned repositories.

Cloning a security tool is not the same as being able to run it. Most of these
repositories need a build or a dependency install first, and doing that by hand
dozens of times is the gap between "cloned" and "usable".

What this does NOT do is run whatever the repository suggests. An ``install.sh``
from a freshly cloned repository is arbitrary code from the internet, and a tool
that executes dozens of them unattended is a supply-chain incident waiting to
happen. Only declarative, recognised build systems are used:

===================  ============================================
``go.mod``           ``go install ./...``
``pyproject.toml``   ``pipx install <dir>``
``setup.py``         ``pipx install <dir>``
``requirements.txt`` a virtualenv inside the clone, then ``pip install -r``
``package.json``     ``npm install --omit=dev`` inside the clone
===================  ============================================

Even these run code -- a ``setup.py`` or an npm postinstall hook can do anything
-- which is why the whole thing is opt-in behind ``--install`` and reports
exactly what it ran. Anything else is reported as needing manual steps, and
repositories that are pure data (wordlists, payload collections, reading lists)
are correctly reported as having nothing to install.
"""

from __future__ import annotations

import enum
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

#: Installs are disk and CPU bound, unlike clones, so they run far less wide.
DEFAULT_INSTALL_WORKERS = 4
DEFAULT_INSTALL_TIMEOUT = 900


class Outcome(enum.Enum):
    """What happened to one repository."""

    INSTALLED = "installed"
    #: Nothing to install -- wordlists, payload collections, reading lists.
    NOTHING = "nothing"
    #: A build system we recognise but cannot drive (MSBuild, bare Makefile).
    MANUAL = "manual"
    #: The required toolchain is not on this machine.
    MISSING_TOOL = "missing-tool"
    FAILED = "failed"
    SKIPPED = "skipped"

    @property
    def ok(self) -> bool:
        return self in (Outcome.INSTALLED, Outcome.NOTHING)


@dataclass(frozen=True)
class Recipe:
    """How to set one repository up."""

    #: Short name of the ecosystem, for output.
    kind: str
    #: Executable that must exist for this recipe to run.
    requires: str
    #: Built lazily so the destination directory can be baked in.
    build: object
    #: Human-readable description of what will run.
    describe: str


def _go(path: Path) -> list[list[str]]:
    return [["go", "install", "./..."]]


def _pipx(path: Path) -> list[list[str]]:
    return [["pipx", "install", "--force", str(path)]]


def _venv_requirements(path: Path) -> list[list[str]]:
    venv = path / ".venv"
    python = venv / "bin" / "python"
    return [
        [sys.executable, "-m", "venv", str(venv)],
        [str(python), "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
        [str(python), "-m", "pip", "install", "--quiet", "-r", str(path / "requirements.txt")],
    ]


def _npm(path: Path) -> list[list[str]]:
    return [["npm", "install", "--omit=dev", "--no-audit", "--no-fund"]]


#: Checked in order; the first match wins.
RECIPES: tuple[tuple[str, Recipe], ...] = (
    ("go.mod", Recipe("go", "go", _go, "go install ./...")),
    ("pyproject.toml", Recipe("python", "pipx", _pipx, "pipx install .")),
    ("setup.py", Recipe("python", "pipx", _pipx, "pipx install .")),
    (
        "requirements.txt",
        Recipe("python", sys.executable, _venv_requirements, "venv + pip install -r"),
    ),
    ("package.json", Recipe("node", "npm", _npm, "npm install --omit=dev")),
)

#: Build systems we recognise but deliberately do not drive.
MANUAL_MARKERS: tuple[tuple[str, str], ...] = (
    ("Makefile", "has a Makefile; run 'make' yourself if you trust it"),
    ("makefile", "has a Makefile; run 'make' yourself if you trust it"),
    ("CMakeLists.txt", "needs cmake"),
    ("build.gradle", "needs gradle"),
    ("pom.xml", "needs maven"),
    ("Cargo.toml", "needs cargo; run 'cargo install --path .' yourself"),
)


@dataclass
class InstallResult:
    """The outcome of setting one repository up."""

    name: str
    outcome: Outcome
    detail: str = ""
    kind: str = ""
    duration: float = 0.0

    @property
    def ok(self) -> bool:
        return self.outcome.ok


def detect(path: Path) -> Recipe | None:
    """The recipe for a clone, or ``None`` if none applies."""
    for marker, recipe in RECIPES:
        if (path / marker).is_file():
            return recipe
    return None


def manual_reason(path: Path) -> str | None:
    """Why a repository needs hands-on setup, if it does."""
    for marker, reason in MANUAL_MARKERS:
        if (path / marker).is_file():
            return reason
    if any(path.glob("*.sln")) or any(path.glob("*.csproj")):
        return "is a Visual Studio project; build it with MSBuild"
    return None


def _run(command: Sequence[str], *, cwd: Path, timeout: int) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Keep pip and npm from trying to talk to a terminal mid-run.
    env.update({"PIP_DISABLE_PIP_VERSION_CHECK": "1", "npm_config_yes": "true"})
    return subprocess.run(
        list(command),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        env=env,
        check=False,
    )


def install_one(
    path: Path,
    *,
    timeout: int = DEFAULT_INSTALL_TIMEOUT,
    dry_run: bool = False,
) -> InstallResult:
    """Set one cloned repository up."""
    name = path.name
    started = time.monotonic()

    def done(outcome: Outcome, detail: str = "", kind: str = "") -> InstallResult:
        return InstallResult(
            name=name,
            outcome=outcome,
            detail=detail,
            kind=kind,
            duration=time.monotonic() - started,
        )

    if not path.is_dir():
        return done(Outcome.SKIPPED, "not on disk")

    recipe = detect(path)
    if recipe is None:
        reason = manual_reason(path)
        if reason:
            return done(Outcome.MANUAL, reason)
        return done(Outcome.NOTHING, "nothing to build")

    if shutil.which(recipe.requires) is None and not Path(recipe.requires).exists():
        return done(
            Outcome.MISSING_TOOL,
            f"{recipe.requires} is not installed",
            kind=recipe.kind,
        )

    if dry_run:
        return done(Outcome.SKIPPED, f"would run {recipe.describe}", kind=recipe.kind)

    for command in recipe.build(path):
        try:
            proc = _run(command, cwd=path, timeout=timeout)
        except subprocess.TimeoutExpired:
            return done(Outcome.FAILED, f"timed out after {timeout}s", kind=recipe.kind)
        except OSError as exc:
            return done(Outcome.FAILED, str(exc), kind=recipe.kind)
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout or "").strip().splitlines()
            detail = message[-1][:200] if message else f"exited {proc.returncode}"
            return done(Outcome.FAILED, detail, kind=recipe.kind)

    return done(Outcome.INSTALLED, recipe.describe, kind=recipe.kind)


def install_all(
    paths: Sequence[Path],
    *,
    workers: int = DEFAULT_INSTALL_WORKERS,
    timeout: int = DEFAULT_INSTALL_TIMEOUT,
    dry_run: bool = False,
    on_result=None,
) -> list[InstallResult]:
    """Set up every cloned repository, a few at a time."""
    if not paths:
        return []

    workers = max(1, min(workers, DEFAULT_INSTALL_WORKERS, len(paths)))
    results: list[InstallResult] = []

    def work(path: Path) -> InstallResult:
        return install_one(path, timeout=timeout, dry_run=dry_run)

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="rrp-install") as pool:
        for result in pool.map(work, paths):
            results.append(result)
            if on_result is not None:
                on_result(result)
    return results
