"""End-to-end tests for the command line interface."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from rapidrepopull import __version__
from rapidrepopull.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_help_lists_the_legacy_flags(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    for flag in ("-v", "-f", "-t", "-u", "--depth", "--output-dir"):
        assert flag in result.output


def test_version(runner):
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_dry_run_uses_the_bundled_list(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(main, ["--dry-run", "--no-banner"])
    assert result.exit_code == 0
    assert "would go to" in result.output
    assert "github.com/danielmiessler/SecLists.git" in result.output


def test_dry_run_with_a_custom_list(runner, tmp_path):
    listing = tmp_path / "mine.txt"
    listing.write_text("owner/one\nowner/two\n", encoding="utf-8")
    result = runner.invoke(main, ["--dry-run", "--no-banner", "-f", str(listing)])
    assert result.exit_code == 0
    assert "owner/one" in result.output
    assert "owner/two" in result.output
    assert "SecLists" not in result.output, "a custom list must replace the default"


def test_legacy_fileinput_flag_still_works(runner, tmp_path):
    listing = tmp_path / "mine.txt"
    listing.write_text("owner/one\n", encoding="utf-8")
    result = runner.invoke(main, ["--dry-run", "--no-banner", "--fileinput", str(listing)])
    assert result.exit_code == 0
    assert "owner/one" in result.output


def test_legacy_thread_flag_still_works(runner, tmp_path):
    listing = tmp_path / "mine.txt"
    listing.write_text("owner/one\n", encoding="utf-8")
    result = runner.invoke(
        main, ["--dry-run", "--no-banner", "--thread", "8", "-f", str(listing)]
    )
    assert result.exit_code == 0


def test_ssh_flag_changes_the_clone_urls(runner, tmp_path):
    listing = tmp_path / "mine.txt"
    listing.write_text("owner/one\n", encoding="utf-8")
    result = runner.invoke(main, ["--dry-run", "--no-banner", "--ssh", "-f", str(listing)])
    assert "git@github.com:owner/one.git" in result.output


def test_missing_list_file_is_a_clean_error(runner):
    result = runner.invoke(main, ["--no-banner", "-f", "/nope/does-not-exist.txt"])
    assert result.exit_code != 0
    assert "Traceback" not in result.output


def test_bad_depth_is_rejected(runner, tmp_path):
    listing = tmp_path / "mine.txt"
    listing.write_text("owner/one\n", encoding="utf-8")
    result = runner.invoke(main, ["--no-banner", "--depth", "0", "-f", str(listing)])
    assert result.exit_code != 0
    assert "--depth" in result.output


def test_save_list_writes_the_resolved_repositories(runner, tmp_path):
    listing = tmp_path / "mine.txt"
    listing.write_text("owner/one\n# comment\nowner/one\nowner/two\n", encoding="utf-8")
    out = tmp_path / "resolved.txt"
    result = runner.invoke(
        main, ["--dry-run", "--no-banner", "-f", str(listing), "--save-list", str(out)]
    )
    assert result.exit_code == 0
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert lines == [
        "https://github.com/owner/one.git",
        "https://github.com/owner/two.git",
    ]


def test_bad_lines_are_reported_but_do_not_stop_the_run(runner, tmp_path):
    listing = tmp_path / "mine.txt"
    listing.write_text("owner/good\n@@@ junk @@@\nowner/also-good\n", encoding="utf-8")
    result = runner.invoke(main, ["--dry-run", "--no-banner", "-f", str(listing)])
    assert result.exit_code == 0
    assert "owner/good" in result.output
    assert "owner/also-good" in result.output
    assert "unreadable" in result.output


def test_a_url_alone_does_not_also_pull_the_default_list(runner, monkeypatch, tmp_path):
    """In 3.x, -u cloned the scraped repos *and* the whole default list."""
    from rapidrepopull.repolist import parse_repo

    monkeypatch.setattr(
        "rapidrepopull.cli.scrape", lambda *a, **k: [parse_repo("scraped/only")]
    )
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(main, ["--dry-run", "--no-banner", "-u", "https://example.com"])
    assert result.exit_code == 0
    assert "scraped/only" in result.output
    assert "SecLists" not in result.output


def test_file_and_url_combine_when_both_are_given(runner, monkeypatch, tmp_path):
    from rapidrepopull.repolist import parse_repo

    monkeypatch.setattr(
        "rapidrepopull.cli.scrape", lambda *a, **k: [parse_repo("scraped/one")]
    )
    listing = tmp_path / "mine.txt"
    listing.write_text("listed/two\n", encoding="utf-8")
    result = runner.invoke(
        main,
        ["--dry-run", "--no-banner", "-f", str(listing), "-u", "https://example.com"],
    )
    assert result.exit_code == 0
    assert "scraped/one" in result.output
    assert "listed/two" in result.output


def test_scrape_failure_exits_cleanly(runner, monkeypatch):
    from rapidrepopull.scraper import ScrapeError

    def boom(*args, **kwargs):
        raise ScrapeError("could not fetch https://example.com: nope")

    monkeypatch.setattr("rapidrepopull.cli.scrape", boom)
    result = runner.invoke(main, ["--no-banner", "-u", "https://example.com"])
    assert result.exit_code == 2
    assert "Traceback" not in result.output


def test_a_local_default_txt_overrides_the_bundled_one(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("default.txt").write_text("local/override\n", encoding="utf-8")
    result = runner.invoke(main, ["--dry-run", "--no-banner"])
    assert result.exit_code == 0
    assert "local/override" in result.output
    assert "SecLists" not in result.output


def test_clone_run_against_local_repos(runner, tmp_path, make_origin):
    """A real end-to-end run, exercising the exit code and the summary."""
    origins = [make_origin(f"repo{i}") for i in range(3)]
    listing = tmp_path / "list.txt"
    listing.write_text("\n".join(o.as_uri() for o in origins) + "\n", encoding="utf-8")
    out = tmp_path / "cloned"

    result = runner.invoke(
        main, ["--no-banner", "-f", str(listing), "-o", str(out), "-t", "3"]
    )

    assert result.exit_code == 0, result.output
    assert "3 cloned" in result.output
    for origin in origins:
        assert (out / origin.stem / "README.md").exists()


def test_failed_clone_sets_a_nonzero_exit_code(runner, tmp_path):
    listing = tmp_path / "list.txt"
    listing.write_text((tmp_path / "missing.git").as_uri() + "\n", encoding="utf-8")

    result = runner.invoke(
        main, ["--no-banner", "-f", str(listing), "-o", str(tmp_path / "out"), "--retries", "0"]
    )
    assert result.exit_code == 1
    assert "1 failed" in result.output
