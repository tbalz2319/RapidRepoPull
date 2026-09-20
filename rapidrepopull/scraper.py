"""Extracting repository links from a web page.

Used by ``--url``: point it at an "awesome-security" style list and every
repository linked from the page becomes a clone target.  The old version wrote
the links to ``red.txt`` and immediately read the file back in; here the links
are returned directly and saving is an explicit, optional step.
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from rapidrepopull.repolist import Repo, RepoParseError, parse_repo

USER_AGENT = "RapidRepoPull/4.0 (+https://github.com/tbalz2319/RapidRepoPull)"
DEFAULT_TIMEOUT = 30

#: Forge hosts whose ``/owner/repo`` links are real repositories.
FORGE_HOSTS = frozenset({"github.com", "www.github.com", "gitlab.com", "www.gitlab.com",
                         "bitbucket.org", "codeberg.org", "git.sr.ht"})

#: First path segments on GitHub that are site features, not user accounts.
RESERVED_OWNERS = frozenset({
    "about", "account", "apps", "blog", "collections", "contact", "customer-stories",
    "dashboard", "enterprise", "events", "explore", "features", "gist", "git",
    "github", "issues", "join", "login", "logout", "marketplace", "new", "notifications",
    "orgs", "pricing", "pulls", "readme", "search", "security", "settings",
    "signup", "site", "sponsors", "stars", "topics", "trending", "users", "watching",
})

#: Second path segments that mean the link points inside a repo, not at it.
_SUBPAGES = frozenset({
    "issues", "pulls", "wiki", "releases", "blob", "tree", "commit", "commits",
    "actions", "projects", "security", "pulse", "graphs", "settings", "stargazers",
    "watchers", "network", "forks", "branches", "tags", "compare", "discussions",
})


class ScrapeError(RuntimeError):
    """Raised when a page cannot be fetched or contains no repositories."""


def fetch(url: str, *, timeout: int = DEFAULT_TIMEOUT, verify: bool = True) -> str:
    """Download a page and return its HTML."""
    try:
        response = requests.get(
            url,
            timeout=timeout,
            verify=verify,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ScrapeError(f"could not fetch {url}: {exc}") from exc
    return response.text


def _looks_like_repo(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.hostname is None or parsed.hostname.lower() not in FORGE_HOSTS:
        return False
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return False
    if parts[0].lower() in RESERVED_OWNERS:
        return False
    # github.com/owner/repo is a repo; github.com/owner/repo/issues is not.
    if len(parts) > 2 and parts[2].lower() in _SUBPAGES:
        return False
    return not len(parts) > 3


def extract_repos(html: str, *, base_url: str | None = None) -> list[Repo]:
    """Pull every repository link out of a page, in document order, deduplicated."""
    soup = BeautifulSoup(html, "html.parser")
    repos: list[Repo] = []
    seen: set[tuple] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        if base_url:
            href = urljoin(base_url, href)
        # Trim the fragment/query that decorates many links in curated lists.
        href = href.split("#", 1)[0].split("?", 1)[0]
        if not _looks_like_repo(href):
            continue
        try:
            repo = parse_repo(href)
        except RepoParseError:
            continue
        if repo.key in seen:
            continue
        seen.add(repo.key)
        repos.append(repo)

    return repos


def scrape(
    url: str, *, timeout: int = DEFAULT_TIMEOUT, verify: bool = True
) -> list[Repo]:
    """Fetch ``url`` and return the repositories it links to."""
    repos = extract_repos(fetch(url, timeout=timeout, verify=verify), base_url=url)
    if not repos:
        raise ScrapeError(f"no repository links found on {url}")
    return repos


def repos_to_lines(repos: Iterable[Repo]) -> list[str]:
    """Render repositories as clone URLs, one per line."""
    return [repo.url() for repo in repos]
