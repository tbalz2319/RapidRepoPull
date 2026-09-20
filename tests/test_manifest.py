"""Tests for the run manifest and --prune."""

import json

import pytest
from click.testing import CliRunner

from rapidrepopull import manifest as manifest_mod
from rapidrepopull.cli import main
from rapidrepopull.cloner import Result, Status
from rapidrepopull.repolist import Repo


@pytest.fixture
def local_list(tmp_path, make_origin):
    """A list file of two throwaway local repositories."""
    alpha = make_origin("alpha")
    bravo = make_origin("bravo")
    path = tmp_path / "list.txt"
    path.write_text(f"file://{alpha}\nfile://{bravo}\n", encoding="utf-8")
    return path, alpha, bravo


def _run(args):
    return CliRunner().invoke(main, [*args, "--no-banner"])


def test_a_run_writes_a_manifest(tmp_path, local_list):
    list_path, _, _ = local_list
    out = tmp_path / "out"
    result = _run(["-f", str(list_path), "-o", str(out)])
    assert result.exit_code == 0

    data = json.loads((out / manifest_mod.MANIFEST_NAME).read_text())
    assert data["version"] == manifest_mod.SCHEMA_VERSION
    # file:// remotes are keyed by their path, so compare on the clone name.
    assert {e["name"] for e in data["repos"].values()} == {"alpha", "bravo"}
    for entry in data["repos"].values():
        assert len(entry["commit"]) == 40


def test_no_manifest_suppresses_the_file(tmp_path, local_list):
    list_path, _, _ = local_list
    out = tmp_path / "out"
    assert _run(["-f", str(list_path), "-o", str(out), "--no-manifest"]).exit_code == 0
    assert not (out / manifest_mod.MANIFEST_NAME).exists()


def test_a_second_run_reports_what_moved(tmp_path, local_list, commit_to):
    list_path, alpha, _ = local_list
    out = tmp_path / "out"
    _run(["-f", str(list_path), "-o", str(out)])

    commit_to(alpha, "second")
    result = _run(["-f", str(list_path), "-o", str(out)])
    assert result.exit_code == 0
    assert "1 updated" in result.output
    assert "alpha" in result.output


def test_an_unchanged_second_run_reports_nothing_moved(tmp_path, local_list):
    list_path, _, _ = local_list
    out = tmp_path / "out"
    _run(["-f", str(list_path), "-o", str(out)])
    result = _run(["-f", str(list_path), "-o", str(out)])
    assert "Commits recorded" not in result.output


def test_a_corrupt_manifest_does_not_stop_a_run(tmp_path, local_list):
    list_path, _, _ = local_list
    out = tmp_path / "out"
    out.mkdir()
    (out / manifest_mod.MANIFEST_NAME).write_text("{ not json", encoding="utf-8")
    result = _run(["-f", str(list_path), "-o", str(out)])
    assert result.exit_code == 0
    assert json.loads((out / manifest_mod.MANIFEST_NAME).read_text())["repos"]


def test_prune_removes_clones_that_left_the_list(tmp_path, local_list):
    list_path, alpha, _ = local_list
    out = tmp_path / "out"
    _run(["-f", str(list_path), "-o", str(out)])
    assert (out / "bravo").is_dir()

    shrunk = tmp_path / "shrunk.txt"
    shrunk.write_text(f"file://{alpha}\n", encoding="utf-8")
    result = _run(["-f", str(shrunk), "-o", str(out), "--prune", "--yes"])

    assert result.exit_code == 0
    assert (out / "alpha").is_dir()
    assert not (out / "bravo").exists()
    data = json.loads((out / manifest_mod.MANIFEST_NAME).read_text())
    assert {e["name"] for e in data["repos"].values()} == {"alpha"}


def test_prune_leaves_directories_it_did_not_clone(tmp_path, local_list):
    list_path, alpha, _ = local_list
    out = tmp_path / "out"
    _run(["-f", str(list_path), "-o", str(out)])

    stranger = out / "not-ours"
    (stranger / ".git").mkdir(parents=True)

    shrunk = tmp_path / "shrunk.txt"
    shrunk.write_text(f"file://{alpha}\n", encoding="utf-8")
    _run(["-f", str(shrunk), "-o", str(out), "--prune", "--yes"])

    assert stranger.is_dir()


def test_prune_declined_keeps_everything(tmp_path, local_list):
    list_path, alpha, _ = local_list
    out = tmp_path / "out"
    _run(["-f", str(list_path), "-o", str(out)])

    shrunk = tmp_path / "shrunk.txt"
    shrunk.write_text(f"file://{alpha}\n", encoding="utf-8")
    result = CliRunner().invoke(
        main, ["-f", str(shrunk), "-o", str(out), "--prune", "--no-banner"], input="n\n"
    )
    assert result.exit_code == 0
    assert (out / "bravo").is_dir()


def test_prune_ignores_the_tag_subset(tmp_path, make_origin):
    """A tagged run must not decide the other tags have left the list."""
    alpha = make_origin("alpha")
    bravo = make_origin("bravo")
    tagged = tmp_path / "tagged.txt"
    tagged.write_text(
        f"# @tag: one\nfile://{alpha}\n# @tag: two\nfile://{bravo}\n", encoding="utf-8"
    )
    out = tmp_path / "out"
    _run(["-f", str(tagged), "-o", str(out)])

    result = _run(["-f", str(tagged), "-o", str(out), "--tag", "one", "--prune", "--yes"])
    assert result.exit_code == 0
    assert (out / "bravo").is_dir(), "pruned a repo that is still in the list"


def test_dry_run_prune_reports_without_deleting(tmp_path, local_list):
    list_path, alpha, _ = local_list
    out = tmp_path / "out"
    _run(["-f", str(list_path), "-o", str(out)])

    shrunk = tmp_path / "shrunk.txt"
    shrunk.write_text(f"file://{alpha}\n", encoding="utf-8")
    result = _run(["-f", str(shrunk), "-o", str(out), "--prune", "--dry-run"])

    assert "would be removed" in result.output
    assert (out / "bravo").is_dir()


def test_stale_ignores_entries_whose_directory_is_gone(tmp_path):
    manifest = manifest_mod.Manifest(path=tmp_path / manifest_mod.MANIFEST_NAME)
    manifest.entries["owner/vanished"] = manifest_mod.Entry(
        slug="owner/vanished", url="https://github.com/owner/vanished.git", name="vanished"
    )
    assert manifest_mod.stale(manifest, [], output_dir=tmp_path) == []


def test_record_skips_failures(tmp_path, git_binary):
    manifest = manifest_mod.Manifest(path=tmp_path / manifest_mod.MANIFEST_NAME)
    failed = Result(repo=Repo(host="github.com", path="o/x"), status=Status.FAILED)
    changes = manifest_mod.record(manifest, [failed], git=git_binary, output_dir=tmp_path)
    assert changes == []
    assert manifest.entries == {}
