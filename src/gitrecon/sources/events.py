"""Listening on GitHub Events API feeds.

The API keeps only the latest 300 events (max 90 days) per feed, so a feed is
polled with ``If-None-Match`` - a ``304`` does not count against the rate
limit - respecting ``X-Poll-Interval``. Seen ids deduplicate overlapping pages.
"""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gitrecon.sources.github_api import GitHubClient

log = logging.getLogger(__name__)

SEEN_IDS_KEPT = 5000


@dataclass(frozen=True)
class Feed:
    """One Events API endpoint: public, user, org or repo."""

    scope: str  # "public" | "user" | "org" | "repo"
    target: str = ""

    @property
    def path(self) -> str:
        match self.scope:
            case "public":
                return "/events"
            case "user":
                return f"/users/{self.target}/events/public"
            case "org":
                return f"/orgs/{self.target}/events"
            case "repo":
                return f"/repos/{self.target}/events"
        raise ValueError(f"unknown feed scope: {self.scope}")

    @property
    def name(self) -> str:
        return self.scope if self.scope == "public" else f"{self.scope}-{self.target.replace('/', '__')}"

    @classmethod
    def parse(cls, spec: str) -> Feed:
        """``public``, ``user:octocat``, ``org:github``, ``repo:owner/name``."""
        scope, _, target = spec.partition(":")
        feed = cls(scope, target)
        feed.path  # validates scope
        return feed


@dataclass
class FeedState:
    etag: str | None = None
    poll_interval: int = 60
    seen: deque[str] = field(default_factory=lambda: deque(maxlen=SEEN_IDS_KEPT))

    def to_dict(self) -> dict[str, Any]:
        return {"etag": self.etag, "poll_interval": self.poll_interval, "seen": list(self.seen)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeedState:
        state = cls(etag=data.get("etag"), poll_interval=data.get("poll_interval", 60))
        state.seen.extend(data.get("seen", []))
        return state


@dataclass
class EventPoller:
    client: GitHubClient
    feed: Feed
    state_dir: Path | None = None
    max_pages: int = 3  # 3 x 100 = whole 300-event window
    state: FeedState = field(init=False)

    def __post_init__(self) -> None:
        self.state = FeedState()
        if self._state_file and self._state_file.exists():
            self.state = FeedState.from_dict(json.loads(self._state_file.read_text()))

    @property
    def _state_file(self) -> Path | None:
        return self.state_dir / f"feed-{self.feed.name}.json" if self.state_dir else None

    def save_state(self) -> None:
        if self._state_file:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(json.dumps(self.state.to_dict()))

    def poll(self) -> list[dict[str, Any]]:
        """One pass over the feed; returns only events not seen before, oldest first."""
        first = self.client.get(self.feed.path, params={"per_page": 100}, etag=self.state.etag)
        if first.poll_interval:
            self.state.poll_interval = first.poll_interval
        if first.not_modified:
            return []
        self.state.etag = first.etag

        fresh: list[dict[str, Any]] = []
        seen = set(self.state.seen)
        response, pages = first, 1
        while True:
            page = response.data or []
            new = [e for e in page if str(e.get("id")) not in seen]
            fresh.extend(new)
            # Stop once a page overlaps with what we already have.
            if len(new) < len(page) or not response.next_url or pages >= self.max_pages:
                break
            response, pages = self.client.get(response.next_url), pages + 1

        fresh.sort(key=lambda e: int(e["id"]))
        self.state.seen.extend(str(e["id"]) for e in fresh)
        self.save_state()
        return fresh

    def listen(self, max_rounds: int | None = None) -> Iterator[list[dict[str, Any]]]:
        """Poll forever (or ``max_rounds`` times), yielding each batch of new events."""
        rounds = 0
        while max_rounds is None or rounds < max_rounds:
            batch = self.poll()
            log.info("%s: %d new events", self.feed.name, len(batch))
            yield batch
            rounds += 1
            if max_rounds is None or rounds < max_rounds:
                time.sleep(self.state.poll_interval)
