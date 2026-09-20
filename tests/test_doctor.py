"""Tests for the list health check and --fix rewriter."""

import pytest
import requests
from click.testing import CliRunner

from rapidrepopull import doctor
from rapidrepopull.cli import main
from rapidrepopull.doctor import State, apply_fixes, check_github, summarise
from rapidrepopull.repolist import Repo, load_list


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = headers or {}

    def json(self):
        if self._payload is _BAD_JSON:
            raise ValueError("not json")
        return self._payload


_BAD_JSON = object()


class FakeSession:
    """Answers GitHub API calls from a dict keyed by owner/repo."""

    def __init__(self, answers, *, raises=None):
        self.answers = answers
        self.raises = raises
        self.calls = []

    def get(self, url, **kwargs):
        slug = url.split("/repos/", 1)[1]
        self.calls.append(slug)
        if self.raises is not None:
            raise self.raises
        return self.answers.get(slug, FakeResponse(404))

    def close(self):
        pass


def repo(path="owner/repo"):
    return Repo(host="github.com", path=path)


def fresh(**extra):
    payload = {"full_name": "owner/repo", "archived": False, "pushed_at": "2026-09-01T00:00:00Z"}
    payload.update(extra)
    return FakeResponse(200, payload)


def _check(response, *, path="owner/repo", **kwargs):
    session = FakeSession({path: response})
    return check_github(repo(path), session=session, token=None, **kwargs)


def test_a_healthy_repository_is_ok():
    finding = _check(fresh())
    assert finding.state is State.OK
    assert finding.ok


def test_a_deleted_repository_is_missing():
    finding = _check(FakeResponse(404))
    assert finding.state is State.MISSING
    assert finding.state.is_fatal


def test_a_rename_is_detected_and_carries_the_new_location():
    finding = _check(fresh(full_name="neworg/repo"))
    assert finding.state is State.RENAMED
    assert finding.replacement == Repo(host="github.com", path="neworg/repo")
    assert "neworg/repo" in finding.detail


def test_a_case_only_difference_is_not_a_rename():
    finding = _check(fresh(full_name="Owner/Repo"))
    assert finding.state is State.OK


def test_an_archived_repository_is_flagged():
    finding = _check(fresh(archived=True))
    assert finding.state is State.ARCHIVED
    assert not finding.state.is_fatal


def test_an_old_repository_is_stale():
    finding = _check(fresh(pushed_at="2015-01-01T00:00:00Z"))
    assert finding.state is State.STALE
    assert "years" in finding.detail


def test_stale_days_is_configurable():
    finding = _check(fresh(pushed_at="2015-01-01T00:00:00Z"), stale_days=100_000)
    assert finding.state is State.OK


def test_a_rename_wins_over_staleness():
    finding = _check(fresh(full_name="neworg/repo", pushed_at="2015-01-01T00:00:00Z"))
    assert finding.state is State.RENAMED


def test_the_rate_limit_is_reported_rather_than_guessed_at():
    finding = _check(FakeResponse(403, headers={"X-RateLimit-Remaining": "0"}))
    assert finding.state is State.RATE_LIMITED
    assert "GITHUB_TOKEN" in finding.detail


def test_a_403_with_quota_left_means_private():
    finding = _check(FakeResponse(403, headers={"X-RateLimit-Remaining": "57"}))
    assert finding.state is State.PRIVATE


def test_a_bad_token_is_reported_as_such():
    finding = _check(FakeResponse(401, headers={"X-RateLimit-Remaining": "57"}))
    assert finding.state is State.ERROR
    assert "token" in finding.detail


def test_a_network_failure_is_an_error_not_a_deletion():
    session = FakeSession({}, raises=requests.RequestException("boom"))
    finding = check_github(repo(), session=session, token=None)
    assert finding.state is State.ERROR
    assert not finding.state.is_fatal


def test_unparseable_json_is_an_error():
    finding = _check(FakeResponse(200, _BAD_JSON))
    assert finding.state is State.ERROR


def test_a_token_is_sent_when_present(monkeypatch):
    seen = {}

    class Recording(FakeSession):
        def get(self, url, **kwargs):
            seen.update(kwargs.get("headers", {}))
            return fresh()

    check_github(repo(), session=Recording({}), token="secret")
    assert seen["Authorization"] == "Bearer secret"


@pytest.mark.parametrize("var", ["RRP_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"])
def test_the_token_is_read_from_the_environment(monkeypatch, var):
    for name in doctor.TOKEN_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(var, "  tok  ")
    assert doctor.find_token() == "tok"


def test_no_token_configured():
    import os

    saved = {n: os.environ.pop(n, None) for n in doctor.TOKEN_ENV_VARS}
    try:
        assert doctor.find_token() is None
    finally:
        for name, value in saved.items():
            if value is not None:
                os.environ[name] = value


def test_summarise_puts_the_worst_first():
    findings = [
        doctor.Finding(repo("a/ok"), State.OK),
        doctor.Finding(repo("a/stale"), State.STALE),
        doctor.Finding(repo("a/gone"), State.MISSING),
    ]
    assert list(summarise(findings)) == [State.MISSING, State.STALE, State.OK]


# --- the rewriter ---------------------------------------------------------

LIST = """\
# header comment

# --- Recon ---
# @tag: recon
https://github.com/old/name.git
https://github.com/dead/repo.git
owner/shorthand
https://github.com/fine/repo.git    # keep this comment
"""


@pytest.fixture
def list_file(tmp_path):
    path = tmp_path / "list.txt"
    path.write_text(LIST, encoding="utf-8")
    return path


def test_fix_rewrites_a_rename_and_keeps_the_url_style(list_file):
    findings = [
        doctor.Finding(
            repo("old/name"), State.RENAMED, "moved to new/name", replacement=repo("new/name")
        )
    ]
    fixes = apply_fixes(list_file, findings)
    text = list_file.read_text()
    assert len(fixes) == 1
    assert "https://github.com/new/name.git" in text
    assert "renamed from old/name" in text
    assert "https://github.com/old/name.git\n" not in text


def test_fix_keeps_shorthand_entries_short(list_file):
    findings = [
        doctor.Finding(
            repo("owner/shorthand"),
            State.RENAMED,
            "moved to owner/renamed",
            replacement=repo("owner/renamed"),
        )
    ]
    apply_fixes(list_file, findings)
    assert "owner/renamed    # renamed from" in list_file.read_text()


def test_fix_comments_out_a_deleted_repository(list_file):
    findings = [doctor.Finding(repo("dead/repo"), State.MISSING, "no longer exists on GitHub")]
    apply_fixes(list_file, findings)
    text = list_file.read_text()
    assert "#https://github.com/dead/repo.git" in text
    assert "no longer exists on GitHub" in text


def test_fix_annotates_an_archived_repository_without_disabling_it(list_file):
    findings = [doctor.Finding(repo("fine/repo"), State.ARCHIVED, "archived by its owner")]
    apply_fixes(list_file, findings)
    line = next(ln for ln in list_file.read_text().splitlines() if "fine/repo" in ln)
    assert not line.lstrip().startswith("#")
    assert "keep this comment" in line
    assert "archived by its owner" in line


def test_fix_is_idempotent(list_file):
    findings = [doctor.Finding(repo("fine/repo"), State.ARCHIVED, "archived by its owner")]
    apply_fixes(list_file, findings)
    first = list_file.read_text()
    apply_fixes(list_file, findings)
    assert list_file.read_text() == first


def test_fix_preserves_comments_tags_and_order(list_file):
    before = list_file.read_text().splitlines()
    findings = [doctor.Finding(repo("dead/repo"), State.MISSING, "gone")]
    apply_fixes(list_file, findings)
    after = list_file.read_text().splitlines()
    assert len(after) == len(before)
    assert after[0] == "# header comment"
    assert "# @tag: recon" in after
    # the tagged list still parses, and the disabled entry is gone from it
    repos, problems = load_list(list_file)
    assert not problems
    assert all(r.path != "dead/repo" for r in repos)
    assert all("recon" in r.tags for r in repos)


def test_fix_changes_nothing_when_everything_is_healthy(list_file):
    before = list_file.read_text()
    fixes = apply_fixes(list_file, [doctor.Finding(repo("fine/repo"), State.OK)])
    assert fixes == []
    assert list_file.read_text() == before


def test_fix_leaves_untouched_entries_alone(list_file):
    findings = [doctor.Finding(repo("dead/repo"), State.MISSING, "gone")]
    apply_fixes(list_file, findings)
    text = list_file.read_text()
    assert "https://github.com/old/name.git" in text
    assert "owner/shorthand" in text


# --- the CLI --------------------------------------------------------------


def _fake_check_all(findings):
    def _inner(repos, **kwargs):
        return findings

    return _inner


def test_doctor_reports_and_exits_zero_when_only_advisory(monkeypatch, list_file):
    monkeypatch.setattr(
        doctor,
        "check_all",
        _fake_check_all([doctor.Finding(repo("a/b"), State.ARCHIVED, "archived by its owner")]),
    )
    result = CliRunner().invoke(main, ["-f", str(list_file), "--doctor", "--no-banner"])
    assert result.exit_code == 0
    assert "Archived upstream" in result.output


def test_doctor_exits_nonzero_when_something_is_gone(monkeypatch, list_file):
    monkeypatch.setattr(
        doctor,
        "check_all",
        _fake_check_all([doctor.Finding(repo("a/b"), State.MISSING, "gone")]),
    )
    result = CliRunner().invoke(main, ["-f", str(list_file), "--doctor", "--no-banner"])
    assert result.exit_code == 1
    assert "Gone from GitHub" in result.output


def test_doctor_fix_writes_the_file(monkeypatch, list_file):
    monkeypatch.setattr(
        doctor,
        "check_all",
        _fake_check_all(
            [
                doctor.Finding(
                    repo("old/name"),
                    State.RENAMED,
                    "moved to new/name",
                    replacement=repo("new/name"),
                )
            ]
        ),
    )
    result = CliRunner().invoke(
        main, ["-f", str(list_file), "--doctor", "--fix", "--no-banner"]
    )
    assert result.exit_code == 0
    assert "Rewrote 1 line" in result.output
    assert "new/name" in list_file.read_text()


def test_doctor_fix_without_a_list_file_is_refused(monkeypatch):
    monkeypatch.setattr(doctor, "check_all", _fake_check_all([]))
    result = CliRunner().invoke(main, ["--doctor", "--fix", "--no-banner"])
    assert result.exit_code == 2
    assert "needs a list file" in result.output


def test_doctor_warns_when_rate_limited(monkeypatch, list_file):
    monkeypatch.setattr(
        doctor,
        "check_all",
        _fake_check_all([doctor.Finding(repo("a/b"), State.RATE_LIMITED, "limit reached")]),
    )
    result = CliRunner().invoke(main, ["-f", str(list_file), "--doctor", "--no-banner"])
    assert "not trustworthy" in result.output
