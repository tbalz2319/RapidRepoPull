"""A record of what was cloned, so a run can be compared with the last one.

RapidRepoPull writes ``.rapidrepopull.json`` into the output directory after
every run: the URL, tags and checked-out commit of each repository it handled.
That buys two things the tool could not do before.

Reproducibility: the commit each clone sat at is written down, so "it worked
last week" is answerable, and a corpus of wordlists and payload collections can
be pinned to a known state rather than silently drifting.

Safe pruning: because the manifest says what RapidRepoPull itself put in the
directory, ``--prune`` can offer to remove clones whose entries have left the
list without ever touching a directory it did not create.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from rapidrepopull.repolist import Repo

#: Name of the manifest inside the output directory.
MANIFEST_NAME = ".rapidrepopull.json"
#: Bumped if the on-disk shape ever changes incompatibly.
SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Entry:
    """One repository as the manifest remembers it."""

    slug: str
    url: str
    name: str
    commit: str | None = None
    tags: list[str] = field(default_factory=list)
    last_seen: str = ""

    def to_json(self) -> dict:
        return {
            "url": self.url,
            "name": self.name,
            "commit": self.commit,
            "tags": sorted(self.tags),
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_json(cls, slug: str, data: dict) -> Entry:
        return cls(
            slug=slug,
            url=str(data.get("url", "")),
            name=str(data.get("name", "")) or slug.rsplit("/", 1)[-1],
            commit=data.get("commit") or None,
            tags=list(data.get("tags") or []),
            last_seen=str(data.get("last_seen", "")),
        )


@dataclass
class Manifest:
    """The manifest for one output directory."""

    path: Path
    entries: dict[str, Entry] = field(default_factory=dict)
    updated_at: str = ""

    @property
    def output_dir(self) -> Path:
        return self.path.parent

    def get(self, slug: str) -> Entry | None:
        return self.entries.get(slug)

    def save(self) -> None:
        self.updated_at = _now()
        payload = {
            "version": SCHEMA_VERSION,
            "updated_at": self.updated_at,
            "repos": {slug: e.to_json() for slug, e in sorted(self.entries.items())},
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.path)


def load(output_dir: Path) -> Manifest:
    """Read the manifest for ``output_dir``, or return an empty one.

    A corrupt or unreadable manifest is treated as absent: it is a cache of
    what happened, never the source of truth, so a bad one must not stop a run.
    """
    path = output_dir / MANIFEST_NAME
    manifest = Manifest(path=path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return manifest
    if not isinstance(data, dict) or data.get("version") != SCHEMA_VERSION:
        return manifest
    repos = data.get("repos")
    if isinstance(repos, dict):
        for slug, entry in repos.items():
            if isinstance(entry, dict):
                manifest.entries[slug] = Entry.from_json(slug, entry)
    manifest.updated_at = str(data.get("updated_at", ""))
    return manifest


def head_commit(repo_dir: Path, *, git: str, timeout: int = 30) -> str | None:
    """The commit a clone is sitting on, or ``None`` if it cannot be read."""
    try:
        proc = subprocess.run(
            [git, "rev-parse", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


@dataclass
class Change:
    """A repository whose commit moved between two runs."""

    slug: str
    before: str | None
    after: str

    @property
    def is_new(self) -> bool:
        return self.before is None

    def short(self) -> str:
        if self.is_new:
            return f"new at {self.after[:8]}"
        return f"{self.before[:8]} -> {self.after[:8]}"


def record(
    manifest: Manifest,
    results,
    *,
    git: str,
    output_dir: Path,
) -> list[Change]:
    """Fold a run's successful results into ``manifest``.

    Returns the repositories whose commit differs from the previous run, which
    is what makes "nothing changed" distinguishable from "everything updated".
    """
    changes: list[Change] = []
    for result in results:
        if not result.ok or result.path is None:
            continue
        repo: Repo = result.repo
        commit = head_commit(result.path, git=git)
        previous = manifest.get(repo.slug)
        before = previous.commit if previous else None
        if commit and commit != before:
            changes.append(Change(slug=repo.slug, before=before, after=commit))
        manifest.entries[repo.slug] = Entry(
            slug=repo.slug,
            url=repo.url(),
            name=repo.name,
            commit=commit or before,
            tags=sorted(repo.tags),
            last_seen=_now(),
        )
    return changes


def stale(manifest: Manifest, repos, *, output_dir: Path) -> list[Entry]:
    """Manifest entries that are no longer in the list but still on disk.

    Only directories RapidRepoPull recorded are considered, so anything else in
    the output directory is left alone.
    """
    current = {repo.slug for repo in repos}
    out: list[Entry] = []
    for slug, entry in sorted(manifest.entries.items()):
        if slug in current:
            continue
        if (output_dir / entry.name / ".git").exists():
            out.append(entry)
    return out
