"""Blog harvesting: article links from an index page, articles as markdown, feed discovery.

Ported from gist ``cc01edd52d24f7f7c20ffb6f561e2874`` (Apokryf blog scraping).
"""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

import bs4
import markdownify
import requests

from gitrecon.models.blog_article import BlogArticle

APOKRYF_BLOG_URL = "https://blog.apokryf.pl"
FEED_TYPES = {"application/rss+xml", "application/atom+xml", "application/rdf+xml"}


def fetch_html(url: str, timeout: float = 60) -> str:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "gitrecon"})
    response.raise_for_status()
    return response.text


def article_links(html: str, base_url: str, suffix: str = ".html") -> list[str]:
    """Distinct links on the page that stay on ``base_url`` and end with ``suffix``."""
    soup = bs4.BeautifulSoup(html, "html.parser")
    base = base_url.rstrip("/")
    links = set()
    for anchor in soup.find_all("a", href=True):
        href = urljoin(base + "/", anchor["href"]).split("#", 1)[0]
        if href.startswith(base) and href.endswith(suffix):
            links.add(href)
    return sorted(links)


def discover_feeds(html: str, page_url: str) -> list[str]:
    """Feeds a page advertises with ``<link rel="alternate" type="application/rss+xml">``."""
    soup = bs4.BeautifulSoup(html, "html.parser")
    feeds = []
    for link in soup.find_all("link", href=True):
        rel = link.get("rel") or []
        if "alternate" in rel and link.get("type") in FEED_TYPES:
            feeds.append(urljoin(page_url, link["href"]))
    return list(dict.fromkeys(feeds))


def article_name(url: str) -> str:
    """``.../2026/03/report-emergent-collective-narrative.html`` -> ``REPORT EMERGENT COLLECTIVE NARRATIVE``."""
    slug = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1].split(".")[0]
    return " ".join(slug.split("-")).upper()


def html_to_article(url: str, html: str, blog: str = "") -> BlogArticle:
    return BlogArticle(
        url=url,
        blog=blog or f"{urlsplit(url).scheme}://{urlsplit(url).netloc}",
        name=article_name(url),
        markdown=markdownify.markdownify(html),
        fetched_at=datetime.now(timezone.utc),
    )


def harvest_blog(base_url: str = APOKRYF_BLOG_URL, limit: int | None = None) -> list[BlogArticle]:
    """Every article linked from the blog's index page, fetched and converted."""
    links = article_links(fetch_html(base_url), base_url)
    return [html_to_article(url, fetch_html(url), base_url) for url in links[:limit]]
