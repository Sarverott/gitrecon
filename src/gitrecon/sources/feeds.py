"""RSS 2.0 / Atom / RDF (RSS 1.0) feed reading.

Feeds are polled with ``If-None-Match`` / ``If-Modified-Since``, items already seen
are skipped, and new ones land in the raw buffer (source ``feeds``). XML from the
outside world is parsed with ``defusedxml`` (no entity expansion bombs, no external
entities).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element

import requests
from defusedxml import ElementTree

from gitrecon.models.feed_item import FeedItem

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rss1": "http://purl.org/rss/1.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}
SUMMARY_CHARS = 2000
TAG = re.compile(r"<[^>]+>")
SEEN_KEPT = 5000


def _text(element: Element | None) -> str:
    return (element.text or "").strip() if element is not None else ""


def _plain(html: str) -> str:
    """Summaries are often HTML; keep plain text, collapsed and bounded."""
    return " ".join(TAG.sub(" ", html).split())[:SUMMARY_CHARS]


def parse_date(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)  # RFC 822, used by RSS 2.0
        except (TypeError, ValueError):
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _rss_item(feed: str, item: Element) -> FeedItem:
    link = _text(item.find("link"))
    guid = _text(item.find("guid"))
    body = _text(item.find("description")) or _text(item.find("content:encoded", NS))
    authors = [_text(a) for a in item.findall("author") + item.findall("dc:creator", NS) if _text(a)]
    return FeedItem(
        feed=feed,
        id=guid or link or _text(item.find("title")),
        title=_text(item.find("title")),
        link=link or None,
        published=parse_date(_text(item.find("pubDate")) or _text(item.find("dc:date", NS))),
        summary=_plain(body),
        authors=authors,
        categories=[_text(c) for c in item.findall("category") if _text(c)],
    )


def _atom_link(entry: Element) -> str | None:
    links = entry.findall("atom:link", NS)
    for link in links:
        if link.get("rel", "alternate") == "alternate" and link.get("href"):
            return link.get("href")
    return links[0].get("href") if links else None


def _atom_entry(feed: str, entry: Element) -> FeedItem:
    body = _text(entry.find("atom:summary", NS)) or _text(entry.find("atom:content", NS))
    link = _atom_link(entry)
    return FeedItem(
        feed=feed,
        id=_text(entry.find("atom:id", NS)) or link or _text(entry.find("atom:title", NS)),
        title=_text(entry.find("atom:title", NS)),
        link=link,
        published=parse_date(_text(entry.find("atom:published", NS))),
        updated=parse_date(_text(entry.find("atom:updated", NS))),
        summary=_plain(body),
        authors=[_text(a.find("atom:name", NS)) for a in entry.findall("atom:author", NS)
                 if _text(a.find("atom:name", NS))],
        categories=[c.get("term", "") for c in entry.findall("atom:category", NS) if c.get("term")],
    )


def _rdf_item(feed: str, item: Element) -> FeedItem:
    link = _text(item.find("rss1:link", NS))
    return FeedItem(
        feed=feed,
        id=item.get(f"{{{NS['rdf']}}}about") or link,
        title=_text(item.find("rss1:title", NS)),
        link=link or None,
        published=parse_date(_text(item.find("dc:date", NS))),
        summary=_plain(_text(item.find("rss1:description", NS))),
        authors=[_text(a) for a in item.findall("dc:creator", NS) if _text(a)],
        categories=[_text(s) for s in item.findall("dc:subject", NS) if _text(s)],
    )


@dataclass
class ParsedFeed:
    url: str
    format: str  # "rss" | "atom" | "rdf"
    title: str
    items: list[FeedItem]


def parse_feed(content: bytes | str, url: str = "") -> ParsedFeed:
    root = ElementTree.fromstring(content)
    tag = root.tag
    if tag == f"{{{NS['atom']}}}feed":
        entries = [_atom_entry(url, e) for e in root.findall("atom:entry", NS)]
        return ParsedFeed(url, "atom", _text(root.find("atom:title", NS)), entries)
    if tag == "rss":
        channel = root.find("channel")
        items = [_rss_item(url, i) for i in channel.findall("item")] if channel is not None else []
        return ParsedFeed(url, "rss", _text(channel.find("title")) if channel is not None else "", items)
    if tag == f"{{{NS['rdf']}}}RDF":
        items = [_rdf_item(url, i) for i in root.findall("rss1:item", NS)]
        return ParsedFeed(url, "rdf", _text(root.find("rss1:channel/rss1:title", NS)), items)
    raise ValueError(f"not a feed (root element {tag!r})")


def feed_key(url: str) -> str:
    """Short stable name of a feed for state and buffer file names."""
    return hashlib.sha1(url.encode()).hexdigest()[:12]


@dataclass
class FeedState:
    etag: str | None = None
    last_modified: str | None = None
    seen: list[str] = field(default_factory=list)


@dataclass
class FeedReader:
    """Polls feeds and returns only items not seen before; state persists in ``state_file``."""

    state_file: Path | None = None
    user_agent: str = "gitrecon"
    timeout: float = 60
    session: requests.Session = field(default_factory=lambda: requests.Session())
    states: dict[str, FeedState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.state_file and self.state_file.exists():
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
            self.states = {url: FeedState(**state) for url, state in raw.items()}

    def save(self) -> None:
        if self.state_file:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {url: state.__dict__ for url, state in sorted(self.states.items())}
            self.state_file.write_text(json.dumps(data, indent=1), encoding="utf-8")

    def poll(self, url: str) -> list[FeedItem]:
        state = self.states.setdefault(url, FeedState())
        headers = {"User-Agent": self.user_agent}
        if state.etag:
            headers["If-None-Match"] = state.etag
        if state.last_modified:
            headers["If-Modified-Since"] = state.last_modified
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        if response.status_code == 304:
            return []
        response.raise_for_status()
        state.etag = response.headers.get("ETag")
        state.last_modified = response.headers.get("Last-Modified")
        feed = parse_feed(response.content, url)
        seen = set(state.seen)
        fresh = [item for item in feed.items if item.id not in seen]
        state.seen = (state.seen + [item.id for item in fresh])[-SEEN_KEPT:]
        self.save()
        return fresh

    def poll_many(self, urls: list[str]) -> dict[str, list[FeedItem] | Exception]:
        """Poll every feed; one broken feed is reported, not fatal."""
        results: dict[str, Any] = {}
        for url in urls:
            try:
                results[url] = self.poll(url)
            except (requests.RequestException, ValueError, ElementTree.ParseError) as error:
                results[url] = error
        return results
