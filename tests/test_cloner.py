"""Tests for the concurrent git driver."""

from pathlib import Path

import pytest

from rapidrepopull.cloner import (
    Repo,
    Result,
    Status,
    Summary,
    _is_transient,
    clone_all,
    find_git,
    process_repo,
)
from rapidrepopull.repolist import parse_repo


def local(bare: Path) -> Repo:
    """A Repo pointing at a local bare repository.

    file:// rather than a bare path: git ignores --depth on plain local
    clones, and this exercises the real transport layer.
    """
    return parse_repo(bare.as_uri())


def test_find_git_returns_an_executable():
    assert Path(find_git()).name.startswith("git")


def test_find_git_honours_the_override(monkeypatch):
    monkeypatch.setenv("RRP_GIT_BINARY", "/custom/path/to/git")
    assert find_git() == "/custom/path/to/git"


def test_clone_succeeds(tmp_path, make_origin, git_binary):
    origin = make_origin()
    out = tmp_path / "out"
    result = process_repo(local(origin), git=git_binary, output_dir=out)

    assert result.status is Status.CLONED
    assert result.ok
    assert (out / origin.stem / "README.md").read_text() == "hello\n"


def test_missing_remote_fails_without_retrying(tmp_path, git_binary):
    repo = local(tmp_path / "does-not-exist.git")
    result = process_repo(repo, git=git_binary, output_dir=tmp_path / "out", retries=3)

    assert result.status is Status.FAILED
    assert result.attempts == 1, "a missing repo is permanent, not transient"
    assert result.detail


def test_existing_repo_is_updated(tmp_path, make_origin, commit_to, git_binary):
    origin = make_origin()
    out = tmp_path / "out"
    repo = local(origin)

    assert process_repo(repo, git=git_binary, output_dir=out).status is Status.CLONED
    commit_to(origin)
    result = process_repo(repo, git=git_binary, output_dir=out, update=True)

    assert result.status is Status.UPDATED
    assert (out / origin.stem / "NEW.md").exists()


def test_existing_repo_is_skipped_when_updates_are_off(tmp_path, make_origin, git_binary):
    origin = make_origin()
    out = tmp_path / "out"
    repo = local(origin)

    process_repo(repo, git=git_binary, output_dir=out)
    result = process_repo(repo, git=git_binary, output_dir=out, update=False)

    assert result.status is Status.SKIPPED
    assert result.ok


def test_non_repo_directory_in_the_way_is_an_error(tmp_path, make_origin, git_binary):
    origin = make_origin()
    out = tmp_path / "out"
    (out / origin.stem).mkdir(parents=True)
    (out / origin.stem / "junk.txt").write_text("not a repo", encoding="utf-8")

    result = process_repo(local(origin), git=git_binary, output_dir=out)
    assert result.status is Status.FAILED
    assert "not a git repository" in result.detail


def test_shallow_clone_has_one_commit(tmp_path, make_origin, commit_to, git_binary):
    import subprocess

    origin = make_origin()
    commit_to(origin)
    out = tmp_path / "out"

    result = process_repo(local(origin), git=git_binary, output_dir=out, depth=1)
    assert result.status is Status.CLONED

    log = subprocess.run(
        [git_binary, "log", "--oneline"],
        cwd=out / origin.stem,
        capture_output=True,
        text=True,
        check=True,
    )
    assert len(log.stdout.strip().splitlines()) == 1


def test_clone_all_processes_every_repo(tmp_path, make_origin, git_binary):
    origins = [make_origin(f"repo{i}") for i in range(5)]
    out = tmp_path / "out"
    seen = []

    summary = clone_all(
        [local(o) for o in origins],
        output_dir=out,
        workers=4,
        on_result=seen.append,
    )

    assert len(summary.results) == 5
    assert len(seen) == 5
    assert all(r.status is Status.CLONED for r in summary.results)
    assert summary.exit_code == 0
    for origin in origins:
        assert (out / origin.stem / "README.md").exists()


def test_clone_all_reports_partial_failure(tmp_path, make_origin, git_binary):
    good = make_origin("good")
    bad = local(tmp_path / "nope.git")

    summary = clone_all([local(good), bad], output_dir=tmp_path / "out", workers=2, retries=0)

    assert len(summary.of(Status.CLONED)) == 1
    assert len(summary.failures) == 1
    assert summary.exit_code == 1


def test_clone_all_with_no_repos_is_a_no_op(tmp_path):
    summary = clone_all([], output_dir=tmp_path / "out", workers=4)
    assert summary.results == []
    assert summary.exit_code == 0


def test_clone_all_creates_the_output_directory(tmp_path, make_origin, git_binary):
    out = tmp_path / "deeply" / "nested" / "out"
    clone_all([local(make_origin())], output_dir=out, workers=1)
    assert out.is_dir()


def test_workers_are_capped_at_the_repo_count(tmp_path, make_origin, git_binary):
    """Asking for 95 threads to clone 2 repos should not start 95 threads."""
    summary = clone_all(
        [local(make_origin("a")), local(make_origin("b"))],
        output_dir=tmp_path / "out",
        workers=95,
    )
    assert len(summary.results) == 2


@pytest.mark.parametrize(
    "message",
    [
        "fatal: unable to access 'https://github.com/x/y.git': Could not resolve host: github.com",
        "error: RPC failed; curl 56 Recv failure: Connection reset by peer",
        "fatal: the remote end hung up unexpectedly",
        "fatal: early EOF",
    ],
)
def test_transient_errors_are_recognised(message):
    assert _is_transient(message)


@pytest.mark.parametrize(
    "message",
    [
        "fatal: repository 'https://github.com/x/y.git' not found",
        "fatal: destination path 'y' already exists and is not an empty directory.",
        "fatal: Authentication failed",
    ],
)
def test_permanent_errors_are_not_retried(message):
    assert not _is_transient(message)


def test_summary_exit_codes():
    repo = parse_repo("owner/repo")
    ok = Summary(results=[Result(repo=repo, status=Status.CLONED)])
    assert ok.exit_code == 0

    bad = Summary(results=[Result(repo=repo, status=Status.FAILED, detail="boom")])
    assert bad.exit_code == 1

    stopped = Summary(results=[], interrupted=True)
    assert stopped.exit_code == 130


def test_status_ok_flags():
    assert Status.CLONED.ok and Status.UPDATED.ok and Status.SKIPPED.ok
    assert not Status.FAILED.ok
