"""Parsing and normalising the repository lists RapidRepoPull works from.

A list file is plain text: one repository per line, ``#`` starts a comment, and
blank lines are ignored.  Every common way of writing a git remote is accepted::

    owner/repo
    https://github.com/owner/repo
    https://github.com/owner/repo.git
    git@github.com:owner/repo.git
    ssh://git@gitlab.com/group/subgroup/repo.git

Anything that cannot be understood is reported rather than raising, so one bad
line never takes down a run -- the old version crashed with an ``AttributeError``
on the first malformed entry.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_HOST = "github.com"

#: ``git@host:path/to/repo.git``
_SCP_RE = re.compile(r"^(?:(?P<user>[^@/]+)@)?(?P<host>[^:/@]+):(?P<path>[^:]+)$")
#: ``scheme://[user@]host/path/to/repo.git``
_URL_RE = re.compile(
    r"^(?P<scheme>https?|ssh|git)://(?:(?P<user>[^@/]+)@)?(?P<host>[^/:]+)(?::\d+)?/(?P<path>.+)$"
)
#: ``file:///absolute/path/to/repo.git`` -- local mirrors and offline caches
_FILE_RE = re.compile(r"^file://(?P<path>/.*)$")
#: bare ``owner/repo`` (or ``group/subgroup/repo``) with no host of its own
_SHORTHAND_RE = re.compile(r"^[\w.-]+(?:/[\w.-]+)+$")


class RepoParseError(ValueError):
    """Raised when a line in a repository list cannot be read as a git remote."""


#: Host value used for repositories that live on this machine.
LOCAL_HOST = "local"


@dataclass(frozen=True)
class Repo:
    """A single repository to clone."""

    host: str
    path: str  # e.g. "owner/repo", or "group/subgroup/repo" on GitLab
    #: Set for remotes that cannot be rebuilt from host+path, such as ``file://``.
    explicit_url: str | None = None

    @property
    def name(self) -> str:
        """The directory name ``git clone`` would create."""
        return self.path.rsplit("/", 1)[-1]

    @property
    def owner(self) -> str:
        """Everything before the final path segment."""
        return self.path.rsplit("/", 1)[0]

    @property
    def slug(self) -> str:
        """``owner/repo`` -- how the repo is identified in output."""
        return self.path

    @property
    def key(self) -> tuple:
        """Identity used for de-duplication."""
        if self.explicit_url:
            return (self.host, self.explicit_url)
        return (self.host, self.path.lower())

    def url(self, *, ssh: bool = False) -> str:
        """The clone URL, HTTPS by default and SCP-style SSH on request."""
        if self.explicit_url:
            return self.explicit_url
        if ssh:
            return f"git@{self.host}:{self.path}.git"
        return f"https://{self.host}/{self.path}.git"

    def __str__(self) -> str:
        if self.host in (DEFAULT_HOST, LOCAL_HOST):
            return self.slug
        return f"{self.host}/{self.path}"


def _clean_path(path: str) -> str:
    """Strip a leading slash, a trailing slash and a trailing ``.git``."""
    path = path.strip().strip("/")
    if path.lower().endswith(".git"):
        path = path[: -len(".git")]
    return path


def parse_repo(line: str, *, default_host: str = DEFAULT_HOST) -> Repo:
    """Parse one line into a :class:`Repo`.

    Raises:
        RepoParseError: if the line is not a recognisable git remote.
    """
    text = line.strip()
    if not text:
        raise RepoParseError("empty line")

    match = _FILE_RE.match(text)
    if match:
        path = _clean_path(match.group("path"))
        if not path:
            raise RepoParseError(f"missing repository path in {text!r}")
        return Repo(host=LOCAL_HOST, path=path, explicit_url=text)

    match = _URL_RE.match(text)
    if match:
        path = _clean_path(match.group("path"))
        if "/" not in path:
            raise RepoParseError(f"missing repository name in {text!r}")
        return Repo(host=match.group("host").lower(), path=path)

    if "://" not in text:
        match = _SCP_RE.match(text)
        if match:
            path = _clean_path(match.group("path"))
            if "/" not in path:
                raise RepoParseError(f"missing repository name in {text!r}")
            return Repo(host=match.group("host").lower(), path=path)

        if _SHORTHAND_RE.match(text):
            return Repo(host=default_host.lower(), path=_clean_path(text))

    raise RepoParseError(f"not a recognisable git remote: {text!r}")


def parse_lines(
    lines: Iterable[str], *, default_host: str = DEFAULT_HOST
) -> tuple[list[Repo], list[tuple[int, str, str]]]:
    """Parse an iterable of raw lines.

    Comments, blank lines and duplicates are dropped; order is preserved.

    Returns:
        ``(repos, problems)`` where each problem is ``(line_number, text, reason)``.
    """
    repos: list[Repo] = []
    problems: list[tuple[int, str, str]] = []
    seen = set()

    for lineno, raw in enumerate(lines, start=1):
        text = raw.split("#", 1)[0].strip()
        if not text:
            continue
        try:
            repo = parse_repo(text, default_host=default_host)
        except RepoParseError as exc:
            problems.append((lineno, text, str(exc)))
            continue
        if repo.key in seen:
            continue
        seen.add(repo.key)
        repos.append(repo)

    return repos, problems


def load_list(
    path: Path, *, default_host: str = DEFAULT_HOST
) -> tuple[list[Repo], list[tuple[int, str, str]]]:
    """Read and parse a repository list file."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        return parse_lines(handle, default_host=default_host)


def default_list_path() -> Path:
    """Path to the bundled ``default.txt``.

    A ``default.txt`` in the working directory wins, so the old
    "edit default.txt and run it" workflow keeps working; otherwise the
    curated list shipped inside the package is used.
    """
    local = Path("default.txt")
    if local.is_file():
        return local
    return Path(__file__).resolve().parent / "data" / "default.txt"


def dedupe(repos: Sequence[Repo]) -> list[Repo]:
    """Drop duplicate repositories, preserving first-seen order."""
    seen = set()
    out: list[Repo] = []
    for repo in repos:
        if repo.key not in seen:
            seen.add(repo.key)
            out.append(repo)
    return out


def write_list(repos: Iterable[Repo], path: Path, *, header: str | None = None) -> None:
    """Write repositories back out as a list file."""
    with open(path, "w", encoding="utf-8") as handle:
        if header:
            for line in header.splitlines():
                handle.write(f"# {line}\n".rstrip() + "\n" if line else "#\n")
            handle.write("\n")
        for repo in repos:
            handle.write(repo.url() + "\n")
