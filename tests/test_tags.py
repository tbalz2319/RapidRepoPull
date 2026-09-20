"""Tests for tag directives, filtering and --tag/--list-tags."""

import pytest
from click.testing import CliRunner

from rapidrepopull.cli import main
from rapidrepopull.repolist import (
    all_tags,
    default_list_path,
    filter_by_tags,
    load_list,
    normalise_tag,
    parse_lines,
    parse_tag_directive,
)

LIST = """\
# @tag: recon
owner/alpha
owner/bravo

# @tag: web
owner/charlie
owner/delta    # @tag: api

# @tag:
owner/echo
"""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Recon", "recon"),
        ("  Blue Team  ", "blue-team"),
        ("blue_team", "blue-team"),
        ("--web--", "web"),
    ],
)
def test_tags_are_normalised(raw, expected):
    assert normalise_tag(raw) == expected


@pytest.mark.parametrize(
    ("comment", "expected"),
    [
        (" @tag: recon", ["recon"]),
        (" @tags: recon, web", ["recon", "web"]),
        (" @tag:", []),
        (" just a comment", None),
        (" --- Recon and OSINT ---", None),
    ],
)
def test_tag_directives_are_recognised(comment, expected):
    assert parse_tag_directive(comment) == expected


def test_a_directive_applies_until_the_next_one():
    repos, problems = parse_lines(LIST.splitlines())
    assert not problems
    by_name = {r.name: r.tags for r in repos}
    assert by_name["alpha"] == {"recon"}
    assert by_name["bravo"] == {"recon"}
    assert by_name["charlie"] == {"web"}


def test_an_empty_directive_clears_the_tags():
    repos, _ = parse_lines(LIST.splitlines())
    assert {r.name: r.tags for r in repos}["echo"] == frozenset()


def test_a_trailing_comment_adds_tags_to_one_line_only():
    repos, _ = parse_lines(LIST.splitlines())
    by_name = {r.name: r.tags for r in repos}
    assert by_name["delta"] == {"web", "api"}
    assert by_name["charlie"] == {"web"}


def test_a_repo_listed_twice_keeps_the_union_of_its_tags():
    repos, _ = parse_lines(
        ["# @tag: recon", "owner/alpha", "# @tag: web", "owner/alpha"]
    )
    assert len(repos) == 1
    assert repos[0].tags == {"recon", "web"}


def test_all_tags_counts_repositories():
    repos, _ = parse_lines(LIST.splitlines())
    assert all_tags(repos) == {"api": 1, "recon": 2, "web": 2}


def test_filtering_keeps_anything_carrying_any_requested_tag():
    repos, _ = parse_lines(LIST.splitlines())
    matched, unknown = filter_by_tags(repos, ["recon", "api"])
    assert [r.name for r in matched] == ["alpha", "bravo", "delta"]
    assert unknown == []


def test_filtering_reports_tags_nothing_carries():
    repos, _ = parse_lines(LIST.splitlines())
    matched, unknown = filter_by_tags(repos, ["recon", "nonsense"])
    assert [r.name for r in matched] == ["alpha", "bravo"]
    assert unknown == ["nonsense"]


def test_no_requested_tags_means_no_filtering():
    repos, _ = parse_lines(LIST.splitlines())
    matched, unknown = filter_by_tags(repos, [])
    assert len(matched) == len(repos)
    assert unknown == []


@pytest.fixture
def list_file(tmp_path):
    path = tmp_path / "list.txt"
    path.write_text(LIST, encoding="utf-8")
    return path


def test_tag_flag_filters_the_run(list_file):
    result = CliRunner().invoke(
        main, ["-f", str(list_file), "--tag", "recon", "--dry-run", "--no-banner"]
    )
    assert result.exit_code == 0
    assert "alpha" in result.output
    assert "charlie" not in result.output


def test_tag_flag_accepts_a_comma_separated_list(list_file):
    result = CliRunner().invoke(
        main, ["-f", str(list_file), "--tag", "recon,web", "--dry-run", "--no-banner"]
    )
    assert result.exit_code == 0
    for name in ("alpha", "bravo", "charlie", "delta"):
        assert name in result.output
    assert "echo" not in result.output


def test_tag_flag_can_be_repeated(list_file):
    result = CliRunner().invoke(
        main,
        ["-f", str(list_file), "--tag", "recon", "--tag", "api", "--dry-run", "--no-banner"],
    )
    assert result.exit_code == 0
    assert "delta" in result.output
    assert "charlie" not in result.output


def test_an_unknown_tag_alone_is_an_error(list_file):
    result = CliRunner().invoke(
        main, ["-f", str(list_file), "--tag", "nonsense", "--dry-run", "--no-banner"]
    )
    assert result.exit_code == 2
    assert "nonsense" in result.output
    assert "--list-tags" in result.output


def test_list_tags_prints_the_groups(list_file):
    result = CliRunner().invoke(main, ["-f", str(list_file), "--list-tags", "--no-banner"])
    assert result.exit_code == 0
    assert "recon" in result.output
    assert "5 repositories" in result.output
    assert "1 carry no tag" in result.output


def test_list_tags_on_an_untagged_list(tmp_path):
    path = tmp_path / "plain.txt"
    path.write_text("owner/alpha\nowner/bravo\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["-f", str(path), "--list-tags", "--no-banner"])
    assert result.exit_code == 0
    assert "no tags" in result.output


def test_the_bundled_list_is_fully_tagged():
    repos, problems = load_list(default_list_path())
    assert not problems
    untagged = [r.slug for r in repos if not r.tags]
    assert untagged == [], f"untagged entries in the bundled list: {untagged}"
