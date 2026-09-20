"""Shared fixtures.

The cloner tests drive a real ``git`` against real local repositories -- no
network, but also no mocking away the thing under test.
"""

import subprocess
from pathlib import Path

import pytest

from rapidrepopull.cloner import find_git


@pytest.fixture(scope="session")
def git_binary():
    try:
        return find_git()
    except Exception:  # pragma: no cover - git is a hard requirement for these tests
        pytest.skip("git is not installed")


@pytest.fixture
def make_origin(tmp_path, git_binary):
    """Build a throwaway upstream repository and return its path."""
    counter = {"n": 0}

    def _make(name: str = "sample") -> Path:
        counter["n"] += 1
        work = tmp_path / "origins" / f"{name}-work-{counter['n']}"
        work.mkdir(parents=True)
        run = lambda *args: subprocess.run(  # noqa: E731
            [git_binary, *args], cwd=work, check=True, capture_output=True
        )
        run("init", "-q", "-b", "main")
        run("config", "user.email", "test@example.invalid")
        run("config", "user.name", "Test")
        (work / "README.md").write_text("hello\n", encoding="utf-8")
        run("add", "README.md")
        run("commit", "-q", "-m", "initial")

        bare = tmp_path / "origins" / f"{name}.git"
        subprocess.run(
            [git_binary, "clone", "-q", "--bare", str(work), str(bare)],
            check=True,
            capture_output=True,
        )
        return bare

    return _make


@pytest.fixture
def commit_to(git_binary):
    """Add a commit to a bare repository via a temporary working clone."""

    def _commit(bare: Path, message: str = "second") -> None:
        clone = bare.parent / (bare.stem + "-push")
        subprocess.run(
            [git_binary, "clone", "-q", str(bare), str(clone)], check=True, capture_output=True
        )
        run = lambda *args: subprocess.run(  # noqa: E731
            [git_binary, *args], cwd=clone, check=True, capture_output=True
        )
        run("config", "user.email", "test@example.invalid")
        run("config", "user.name", "Test")
        (clone / "NEW.md").write_text(message + "\n", encoding="utf-8")
        run("add", "NEW.md")
        run("commit", "-q", "-m", message)
        run("push", "-q", "origin", "HEAD")

    return _commit
