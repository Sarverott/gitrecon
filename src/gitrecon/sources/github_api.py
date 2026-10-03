"""Thin GitHub REST client: conditional requests, poll intervals, rate limits."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from gitrecon.config import Config

log = logging.getLogger(__name__)


SECONDARY_RETRIES = 3
SECONDARY_WAIT = 60  # seconds, when GitHub sends no Retry-After


def _forbids_classic_token(r: requests.Response) -> bool:
    try:
        message = (r.json() or {}).get("message", "")
    except ValueError:
        return False
    return "forbids access via a personal access token (classic)" in message


def _is_secondary_limit(r: requests.Response) -> bool:
    if "Retry-After" in r.headers:
        return True
    try:
        message = (r.json() or {}).get("message", "")
    except ValueError:
        return False
    return "secondary rate limit" in message.lower() or "abuse" in message.lower()


@dataclass
class Response:
    status: int
    data: Any
    etag: str | None
    poll_interval: int | None
    next_url: str | None
    links: dict[str, dict[str, str]] | None = None

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
    anonymous_fallbacks: int = 0  # requests repeated without the token (orgs refusing classic tokens)
    rate: RateLimit = field(default_factory=RateLimit)
    session: requests.Session = field(default_factory=lambda: requests.Session())

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
        accept: str | None = None,
    ) -> Response:
        url = path_or_url if path_or_url.startswith("http") else self.config.api_url + path_or_url
        headers = {"If-None-Match": etag} if etag else {}
        if accept:
            headers["Accept"] = accept
        secondary_retries = 0
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
            if r.status_code in (403, 429) and secondary_retries < SECONDARY_RETRIES and _is_secondary_limit(r):
                # too many requests too fast: GitHub asks to wait (Retry-After) even with quota left
                secondary_retries += 1
                wait = float(r.headers.get("Retry-After") or SECONDARY_WAIT)
                if not self.wait_on_limit:
                    raise RuntimeError(f"GitHub secondary rate limit, retry in {wait:.0f}s")
                log.warning("secondary rate limit, sleeping %.0fs (attempt %d)", wait, secondary_retries)
                time.sleep(wait)
                continue
            if r.status_code == 403 and "Authorization" not in headers and _forbids_classic_token(r):
                # an organization that refuses classic tokens still shows its public data anonymously
                log.warning("%s refuses classic tokens - retrying without one (public data only)",
                            url.split("?")[0])
                headers["Authorization"] = None  # None drops the session's header for this request
                self.anonymous_fallbacks += 1
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
                links=dict(r.links),
            )

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run a GraphQL query (needs a token); returns ``data``, raises on errors."""
        if not self.config.github_token:
            raise RuntimeError("GitHub GraphQL needs a token (GITHUB_TOKEN, GH_TOKEN or `gh auth login`)")
        r = self.session.post(f"{self.config.api_url}/graphql", json={"query": query, "variables": variables or {}},
                              timeout=60)
        self.rate.update(r.headers)
        r.raise_for_status()
        body = r.json()
        if body.get("errors"):
            raise RuntimeError("; ".join(e.get("message", str(e)) for e in body["errors"]))
        return body["data"]

    def count(self, path: str) -> int:
        """How many items a listing has.

        One request when GitHub sends ``rel="last"`` (``per_page=1``: the last page number is
        the count). Some listings - gist commits - only send ``rel="next"``; those are paged
        through 100 at a time instead.
        """
        response = self.get(path, params={"per_page": 1})
        links = response.links or {}
        if match := re.search(r"[?&]page=(\d+)", links.get("last", {}).get("url", "")):
            return int(match.group(1))
        if "next" not in links:
            return len(response.data or [])
        return sum(1 for _ in self.paginate(path, max_pages=10**6))

    def paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        max_pages: int = 10,
        accept: str | None = None,
    ):
        """Yield items across ``Link: rel=next`` pages."""
        params = {"per_page": 100, **(params or {})}
        url: str | None = path
        for _ in range(max_pages):
            if not url:
                return
            response = self.get(url, params=params, accept=accept)
            params = None  # next_url already carries the query
            yield from response.data or []
            url = response.next_url
