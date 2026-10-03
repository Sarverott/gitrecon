"""Thin GitHub REST client: conditional requests, poll intervals, rate limits."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from gitrecon.config import Config

log = logging.getLogger(__name__)


@dataclass
class Response:
    status: int
    data: Any
    etag: str | None
    poll_interval: int | None
    next_url: str | None

    @property
    def not_modified(self) -> bool:
        return self.status == 304


@dataclass
class RateLimit:
    limit: int | None = None
    remaining: int | None = None
    reset: int | None = None  # unix time

    def update(self, headers: Any) -> None:
        for attr, header in (
            ("limit", "X-RateLimit-Limit"),
            ("remaining", "X-RateLimit-Remaining"),
            ("reset", "X-RateLimit-Reset"),
        ):
            if header in headers:
                setattr(self, attr, int(headers[header]))

    def seconds_to_reset(self) -> float:
        return max(0.0, (self.reset or 0) - time.time())


@dataclass
class GitHubClient:
    config: Config = field(default_factory=Config)
    wait_on_limit: bool = True
    rate: RateLimit = field(default_factory=RateLimit)
    session: requests.Session = field(default_factory=requests.Session)

    def __post_init__(self) -> None:
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": self.config.user_agent,
            }
        )
        if self.config.github_token:
            self.session.headers["Authorization"] = f"Bearer {self.config.github_token}"

    def get(
        self,
        path_or_url: str,
        params: dict[str, Any] | None = None,
        etag: str | None = None,
    ) -> Response:
        url = path_or_url if path_or_url.startswith("http") else self.config.api_url + path_or_url
        headers = {"If-None-Match": etag} if etag else {}
        while True:
            r = self.session.get(url, params=params, headers=headers, timeout=60)
            self.rate.update(r.headers)
            if r.status_code in (403, 429) and self.rate.remaining == 0:
                wait = self.rate.seconds_to_reset() + 1
                if not self.wait_on_limit:
                    raise RuntimeError(f"GitHub rate limit exhausted, resets in {wait:.0f}s")
                log.warning("rate limit exhausted, sleeping %.0fs", wait)
                time.sleep(wait)
                continue
            if r.status_code != 304:
                r.raise_for_status()
            return Response(
                status=r.status_code,
                data=r.json() if r.status_code != 304 and r.content else None,
                etag=r.headers.get("ETag"),
                poll_interval=int(r.headers["X-Poll-Interval"])
                if "X-Poll-Interval" in r.headers
                else None,
                next_url=r.links.get("next", {}).get("url"),
            )

    def paginate(self, path: str, params: dict[str, Any] | None = None, max_pages: int = 10):
        """Yield items across ``Link: rel=next`` pages."""
        params = {"per_page": 100, **(params or {})}
        url: str | None = path
        for _ in range(max_pages):
            if not url:
                return
            response = self.get(url, params=params)
            params = None  # next_url already carries the query
            yield from response.data or []
            url = response.next_url
