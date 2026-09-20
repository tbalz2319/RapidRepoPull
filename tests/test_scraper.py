"""Tests for pulling repository links out of a web page."""

import pytest

from rapidrepopull.scraper import ScrapeError, extract_repos, scrape

PAGE = """
<html><body>
  <h1>Awesome Security</h1>
  <a href="https://github.com/danielmiessler/SecLists">SecLists</a>
  <a href="https://github.com/OJ/gobuster.git">gobuster</a>
  <a href="https://github.com/laramies/theHarvester/">theHarvester</a>

  <!-- not repositories -->
  <a href="https://github.com/features/actions">Actions</a>
  <a href="https://github.com/pricing">Pricing</a>
  <a href="https://github.com/topics/security">Topic</a>
  <a href="https://github.com/sponsors/someone">Sponsor</a>
  <a href="https://github.com/orgs/acme/people">Org</a>
  <a href="https://github.com/OJ/gobuster/issues/42">An issue</a>
  <a href="https://github.com/OJ/gobuster/blob/master/README.md">A file</a>
  <a href="https://github.com/danielmiessler">Just a user</a>
  <a href="https://example.com/not/a/forge">Elsewhere</a>
  <a href="#section">Anchor</a>
  <a href="mailto:me@example.com">Mail</a>

  <!-- duplicates in other spellings -->
  <a href="git@github.com:OJ/gobuster.git">gobuster again</a>
  <a href="https://github.com/oj/GOBUSTER">gobuster yet again</a>

  <!-- other forges -->
  <a href="https://gitlab.com/group/project">GitLab</a>
  <a href="https://codeberg.org/owner/repo">Codeberg</a>
</body></html>
"""


def test_extract_finds_the_real_repositories():
    repos = extract_repos(PAGE)
    slugs = [str(r) for r in repos]
    assert "danielmiessler/SecLists" in slugs
    assert "OJ/gobuster" in slugs
    assert "laramies/theHarvester" in slugs
    assert "gitlab.com/group/project" in slugs
    assert "codeberg.org/owner/repo" in slugs


def test_extract_rejects_site_pages_and_sub_pages():
    slugs = [str(r) for r in extract_repos(PAGE)]
    for unwanted in (
        "features/actions",
        "topics/security",
        "sponsors/someone",
        "orgs/acme",
    ):
        assert unwanted not in slugs
    # A link into a repo must not produce a second entry for that repo.
    assert slugs.count("OJ/gobuster") == 1


def test_extract_deduplicates_across_spellings():
    assert len([r for r in extract_repos(PAGE) if r.name.lower() == "gobuster"]) == 1


def test_extract_preserves_document_order():
    slugs = [str(r) for r in extract_repos(PAGE)]
    assert slugs.index("danielmiessler/SecLists") < slugs.index("OJ/gobuster")


def test_extract_strips_query_and_fragment():
    repos = extract_repos('<a href="https://github.com/owner/repo?tab=readme#top">x</a>')
    assert [str(r) for r in repos] == ["owner/repo"]


def test_extract_resolves_relative_links_against_the_page():
    html = '<a href="/owner/repo">relative</a>'
    assert [str(r) for r in extract_repos(html, base_url="https://github.com/somewhere")] == [
        "owner/repo"
    ]


def test_extract_on_a_page_with_no_repos():
    assert extract_repos("<html><body><p>nothing here</p></body></html>") == []


def test_scrape_raises_when_the_page_has_no_repositories(monkeypatch):
    monkeypatch.setattr("rapidrepopull.scraper.fetch", lambda *a, **k: "<html></html>")
    with pytest.raises(ScrapeError, match="no repository links"):
        scrape("https://example.com")


def test_scrape_wraps_network_errors(monkeypatch):
    import requests

    def boom(*args, **kwargs):
        raise requests.ConnectionError("dns is having a day")

    monkeypatch.setattr("rapidrepopull.scraper.requests.get", boom)
    with pytest.raises(ScrapeError, match="could not fetch"):
        scrape("https://example.com")


def test_scrape_returns_repos(monkeypatch):
    monkeypatch.setattr("rapidrepopull.scraper.fetch", lambda *a, **k: PAGE)
    repos = scrape("https://example.com")
    assert len(repos) >= 5
