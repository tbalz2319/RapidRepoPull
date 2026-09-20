"""Checking a repository list against reality.

A curated list of security tooling rots. Projects get renamed, move to a new
organisation, get archived, or disappear. Nothing in the list itself records
that, so the rot is invisible until a run starts failing -- and a failed clone
looks the same whether the network blipped or the repository no longer exists.

This module asks GitHub about every entry and reports what it finds: renames
(GitHub redirects the API call and returns the new ``full_name``), archived
projects, deletions, and repositories nobody has pushed to in years. With
``--fix`` the answers are written back into the list.

Non-GitHub remotes get a cheaper check: ``git ls-remote`` tells us whether the
remote is still reachable, which is all that can be established generically.
"""

from __future__ import annotations

import enum
import os
import subprocess
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

from rapidrepopull.repolist import DEFAULT_HOST, Repo, RepoParseError, parse_repo

GITHUB_API = "https://api.github.com"
#: GitHub allows 60 unauthenticated calls an hour, 5000 with a token.
TOKEN_ENV_VARS = ("RRP_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN")
#: Anything not pushed to in this long is worth a second look.
DEFAULT_STALE_DAYS = 730
#: The API is rate limited, so this stays well below the clone concurrency.
DEFAULT_CHECK_WORKERS = 8
DEFAULT_CHECK_TIMEOUT = 15


class State(enum.Enum):
    """What the check found."""

    OK = "ok"
    RENAMED = "renamed"
    ARCHIVED = "archived"
    STALE = "stale"
    MISSING = "missing"
    PRIVATE = "private"
    UNREACHABLE = "unreachable"
    RATE_LIMITED = "rate-limited"
    ERROR = "error"

    @property
    def is_problem(self) -> bool:
        return self is not State.OK

    @property
    def is_fatal(self) -> bool:
        """States where the entry cannot be cloned at all."""
        return self in (State.MISSING, State.PRIVATE, State.UNREACHABLE)


@dataclass
class Finding:
    """The outcome of checking one repository."""

    repo: Repo
    state: State
    detail: str = ""
    #: Where the repository moved to, for :attr:`State.RENAMED`.
    replacement: Repo | None = None
    pushed_at: str = ""
    stars: int | None = None

    @property
    def ok(self) -> bool:
        return self.state is State.OK


def find_token() -> str | None:
    """A GitHub token from the environment, if one is set."""
    for name in TOKEN_ENV_VARS:
        value = os.environ.get(name)
        if value:
            return value.strip()
    return None


def _headers(token: str | None) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "rapidrepopull",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _age_days(timestamp: str) -> int | None:
    """Days since an ISO-8601 timestamp, or ``None`` if it cannot be read."""
    if not timestamp:
        return None
    try:
        when = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - when).days


def check_github(
    repo: Repo,
    *,
    session: requests.Session,
    token: str | None,
    stale_days: int = DEFAULT_STALE_DAYS,
    timeout: int = DEFAULT_CHECK_TIMEOUT,
) -> Finding:
    """Ask the GitHub API about one repository."""
    url = f"{GITHUB_API}/repos/{repo.path}"
    try:
        response = session.get(
            url, headers=_headers(token), timeout=timeout, allow_redirects=True
        )
    except requests.RequestException as exc:
        return Finding(repo, State.ERROR, f"could not reach the GitHub API: {exc}")

    if response.status_code == 404:
        return Finding(repo, State.MISSING, "no longer exists on GitHub")

    if response.status_code in (401, 403, 429):
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining == "0" or response.status_code == 429:
            hint = "set GITHUB_TOKEN to raise the limit" if not token else "wait and retry"
            return Finding(repo, State.RATE_LIMITED, f"GitHub rate limit reached; {hint}")
        if response.status_code == 401:
            return Finding(repo, State.ERROR, "GitHub rejected the token")
        return Finding(repo, State.PRIVATE, "private, or access is blocked")

    if response.status_code != 200:
        return Finding(repo, State.ERROR, f"GitHub returned HTTP {response.status_code}")

    try:
        data = response.json()
    except ValueError:
        return Finding(repo, State.ERROR, "GitHub returned a response that was not JSON")

    full_name = str(data.get("full_name") or "")
    pushed_at = str(data.get("pushed_at") or "")
    stars = data.get("stargazers_count")
    stars = stars if isinstance(stars, int) else None

    if full_name and full_name.lower() != repo.path.lower():
        return Finding(
            repo,
            State.RENAMED,
            f"moved to {full_name}",
            replacement=parse_repo(full_name),
            pushed_at=pushed_at,
            stars=stars,
        )

    if data.get("archived"):
        return Finding(
            repo, State.ARCHIVED, "archived by its owner", pushed_at=pushed_at, stars=stars
        )

    age = _age_days(pushed_at)
    if age is not None and age > stale_days:
        years = age / 365.25
        return Finding(
            repo,
            State.STALE,
            f"no push in {years:.1f} years",
            pushed_at=pushed_at,
            stars=stars,
        )

    return Finding(repo, State.OK, pushed_at=pushed_at, stars=stars)


def check_remote(repo: Repo, *, git: str, timeout: int = DEFAULT_CHECK_TIMEOUT) -> Finding:
    """Check a non-GitHub remote by asking git whether it still answers."""
    env = os.environ.copy()
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "echo", "SSH_ASKPASS": "echo"})
    try:
        proc = subprocess.run(
            [git, "ls-remote", "--exit-code", "--heads", repo.url()],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Finding(repo, State.UNREACHABLE, f"no answer within {timeout}s")
    except OSError as exc:
        return Finding(repo, State.ERROR, str(exc))

    if proc.returncode == 0:
        return Finding(repo, State.OK)
    message = (proc.stderr or proc.stdout or "").strip().splitlines()
    detail = message[-1] if message else f"git exited {proc.returncode}"
    return Finding(repo, State.UNREACHABLE, detail)


def check_all(
    repos: Sequence[Repo],
    *,
    git: str,
    token: str | None = None,
    stale_days: int = DEFAULT_STALE_DAYS,
    workers: int = DEFAULT_CHECK_WORKERS,
    timeout: int = DEFAULT_CHECK_TIMEOUT,
    on_result=None,
) -> list[Finding]:
    """Check every repository, GitHub ones through the API and the rest via git."""
    if not repos:
        return []

    session = requests.Session()

    def check(repo: Repo) -> Finding:
        if repo.host == DEFAULT_HOST:
            return check_github(
                repo, session=session, token=token, stale_days=stale_days, timeout=timeout
            )
        return check_remote(repo, git=git, timeout=timeout)

    workers = max(1, min(workers, len(repos)))
    findings: list[Finding] = []
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="rrp-doctor") as pool:
        for finding in pool.map(check, repos):
            findings.append(finding)
            if on_result is not None:
                on_result(finding)

    session.close()
    return findings


def summarise(findings: Sequence[Finding]) -> dict[State, list[Finding]]:
    """Group findings by state, most serious first."""
    order = [
        State.MISSING,
        State.PRIVATE,
        State.UNREACHABLE,
        State.RENAMED,
        State.ARCHIVED,
        State.STALE,
        State.RATE_LIMITED,
        State.ERROR,
        State.OK,
    ]
    grouped = {state: [f for f in findings if f.state is state] for state in order}
    return {state: found for state, found in grouped.items() if found}


#: States whose entries ``--fix`` comments out rather than rewrites.
_DISABLE = (State.MISSING, State.PRIVATE, State.UNREACHABLE)
#: States ``--fix`` annotates in place, leaving the entry active.
_ANNOTATE = (State.ARCHIVED, State.STALE)


@dataclass
class Fix:
    """One line of a list file, changed."""

    lineno: int
    before: str
    after: str
    state: State
    detail: str


def _rewrite_line(line: str, finding: Finding, *, today: str) -> str | None:
    """Apply one finding to the line it came from, or ``None`` to leave it."""
    code, hash_, comment = line.partition("#")
    trailing = f"#{comment}" if hash_ else ""
    stripped = code.strip()
    indent = code[: len(code) - len(code.lstrip())]

    def joined(body: str, note: str) -> str:
        parts = [f"{indent}{body}"]
        if trailing:
            parts.append(trailing.rstrip())
        parts.append(note)
        return "    ".join(p for p in parts if p)

    if finding.state is State.RENAMED and finding.replacement is not None:
        new_url = finding.replacement.url()
        if stripped.endswith(".git") or stripped.startswith(("http", "git@", "ssh://")):
            body = new_url
        else:
            body = finding.replacement.path
        return joined(body, f"# renamed from {finding.repo.path} on {today}")

    if finding.state in _DISABLE:
        return joined(f"#{stripped}", f"# {finding.detail} ({today})")

    if finding.state in _ANNOTATE:
        # Already annotated by an earlier run? Leave it alone.
        if "# archived" in line or "# no push in" in line:
            return None
        return joined(stripped, f"# {finding.detail} ({today})")

    return None


def apply_fixes(path, findings: Sequence[Finding], *, default_host: str = DEFAULT_HOST):
    """Rewrite a list file in place from ``findings``.

    Comments, blank lines, ordering and ``@tag:`` directives are preserved --
    the file is edited line by line rather than regenerated, so a hand-curated
    list stays hand-curated.

    Returns the list of :class:`Fix` objects applied.
    """
    path = Path(path)
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    today = datetime.now(timezone.utc).date().isoformat()

    actionable = {
        f.repo.key: f for f in findings if f.state in (State.RENAMED, *_DISABLE, *_ANNOTATE)
    }
    if not actionable:
        return []

    fixes: list[Fix] = []
    for index, line in enumerate(lines):
        code = line.split("#", 1)[0].strip()
        if not code:
            continue
        try:
            repo = parse_repo(code, default_host=default_host)
        except RepoParseError:
            continue
        finding = actionable.get(repo.key)
        if finding is None:
            continue
        replacement = _rewrite_line(line, finding, today=today)
        if replacement is None or replacement == line:
            continue
        lines[index] = replacement
        fixes.append(
            Fix(
                lineno=index + 1,
                before=line,
                after=replacement,
                state=finding.state,
                detail=finding.detail,
            )
        )

    if fixes:
        trailing_newline = "\n" if original.endswith("\n") else ""
        path.write_text("\n".join(lines) + trailing_newline, encoding="utf-8")
    return fixes
