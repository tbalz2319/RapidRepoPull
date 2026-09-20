"""Tests for parsing repository lists."""

import pytest

from rapidrepopull.repolist import (
    Repo,
    RepoParseError,
    dedupe,
    parse_lines,
    parse_repo,
)


@pytest.mark.parametrize(
    ("line", "host", "path"),
    [
        ("owner/repo", "github.com", "owner/repo"),
        ("https://github.com/owner/repo", "github.com", "owner/repo"),
        ("https://github.com/owner/repo.git", "github.com", "owner/repo"),
        ("https://github.com/owner/repo/", "github.com", "owner/repo"),
        ("http://github.com/owner/repo.git", "github.com", "owner/repo"),
        ("git@github.com:owner/repo.git", "github.com", "owner/repo"),
        ("git@github.com:owner/repo", "github.com", "owner/repo"),
        ("ssh://git@github.com/owner/repo.git", "github.com", "owner/repo"),
        ("git://github.com/owner/repo.git", "github.com", "owner/repo"),
        ("https://gitlab.com/group/subgroup/repo.git", "gitlab.com", "group/subgroup/repo"),
        ("git@gitlab.com:group/subgroup/repo.git", "gitlab.com", "group/subgroup/repo"),
        ("https://codeberg.org/owner/repo", "codeberg.org", "owner/repo"),
        ("https://GitHub.com/Owner/Repo", "github.com", "Owner/Repo"),
        ("https://github.com:443/owner/repo.git", "github.com", "owner/repo"),
    ],
)
def test_parse_repo_accepts_every_common_remote_form(line, host, path):
    repo = parse_repo(line)
    assert repo.host == host
    assert repo.path == path


@pytest.mark.parametrize(
    "line",
    [
        "",
        "   ",
        "not a url at all",
        "https://github.com/owner",
        "https://github.com/",
        "git@github.com:owner",
        "ftp://github.com/owner/repo",
    ],
)
def test_parse_repo_rejects_junk(line):
    with pytest.raises(RepoParseError):
        parse_repo(line)


def test_repo_derives_name_owner_and_urls():
    repo = parse_repo("https://github.com/danielmiessler/SecLists.git")
    assert repo.name == "SecLists"
    assert repo.owner == "danielmiessler"
    assert repo.slug == "danielmiessler/SecLists"
    assert repo.url() == "https://github.com/danielmiessler/SecLists.git"
    assert repo.url(ssh=True) == "git@github.com:danielmiessler/SecLists.git"
    assert str(repo) == "danielmiessler/SecLists"


def test_non_github_host_is_shown_in_full():
    repo = parse_repo("https://gitlab.com/group/repo")
    assert str(repo) == "gitlab.com/group/repo"


def test_gitlab_subgroup_name_is_the_last_segment():
    repo = parse_repo("https://gitlab.com/group/subgroup/repo.git")
    assert repo.name == "repo"
    assert repo.owner == "group/subgroup"


def test_parse_lines_skips_comments_and_blanks():
    repos, problems = parse_lines(
        [
            "# a comment",
            "",
            "   ",
            "owner/one",
            "owner/two  # trailing comment",
            "\t",
        ]
    )
    assert [r.path for r in repos] == ["owner/one", "owner/two"]
    assert problems == []


def test_parse_lines_reports_bad_lines_without_raising():
    """The 3.x parser died on the first malformed entry."""
    repos, problems = parse_lines(["owner/good", "!!! nonsense !!!", "owner/also-good"])
    assert [r.path for r in repos] == ["owner/good", "owner/also-good"]
    assert len(problems) == 1
    lineno, text, _reason = problems[0]
    assert lineno == 2
    assert text == "!!! nonsense !!!"


def test_parse_lines_deduplicates_across_url_forms():
    repos, _ = parse_lines(
        [
            "https://github.com/owner/repo.git",
            "git@github.com:owner/repo.git",
            "owner/repo",
            "https://github.com/OWNER/REPO",
        ]
    )
    assert len(repos) == 1


def test_same_name_on_different_hosts_is_not_a_duplicate():
    repos, _ = parse_lines(["https://github.com/owner/repo", "https://gitlab.com/owner/repo"])
    assert len(repos) == 2


def test_dedupe_preserves_first_seen_order():
    repos = [
        Repo("github.com", "a/one"),
        Repo("github.com", "b/two"),
        Repo("github.com", "A/ONE"),
        Repo("github.com", "c/three"),
    ]
    assert [r.path for r in dedupe(repos)] == ["a/one", "b/two", "c/three"]


def test_load_list_reads_a_file(tmp_path):
    from rapidrepopull.repolist import load_list

    listing = tmp_path / "repos.txt"
    listing.write_text("# header\nowner/one\ngit@github.com:owner/two.git\n", encoding="utf-8")
    repos, problems = load_list(listing)
    assert [r.path for r in repos] == ["owner/one", "owner/two"]
    assert problems == []


def test_bundled_default_list_is_valid():
    """Every uncommented line in the shipped list must parse."""
    from rapidrepopull.repolist import load_list

    bundled = __import__("rapidrepopull").__file__
    from pathlib import Path

    path = Path(bundled).parent / "data" / "default.txt"
    repos, problems = load_list(path)
    assert problems == []
    assert len(repos) > 40
    assert len(dedupe(repos)) == len(repos), "the shipped list contains duplicates"


@pytest.mark.parametrize(
    ("line", "name"),
    [
        ("file:///srv/mirrors/seclists.git", "seclists"),
        ("file:///srv/mirrors/nested/tool.git", "tool"),
        ("file:///srv/mirrors/tool", "tool"),
    ],
)
def test_file_urls_are_supported_for_local_mirrors(line, name):
    repo = parse_repo(line)
    assert repo.host == "local"
    assert repo.name == name
    assert repo.url() == line, "a file:// remote must be passed to git unchanged"
    assert repo.url(ssh=True) == line, "--ssh cannot apply to a local path"


def test_file_urls_with_the_same_name_in_different_places_are_distinct():
    repos, _ = parse_lines(["file:///a/tool.git", "file:///b/tool.git"])
    assert len(repos) == 2


def test_identical_file_urls_are_deduplicated():
    repos, _ = parse_lines(["file:///a/tool.git", "file:///a/tool.git"])
    assert len(repos) == 1


def test_file_url_without_a_path_is_rejected():
    with pytest.raises(RepoParseError):
        parse_repo("file://")
