"""Repositories starred by a user."""

from __future__ import annotations

from typing import Any

from gitrecon.models.star import Star
from gitrecon.sources.github_api import GitHubClient

__all__ = ["Star", "starred", "starred_raw"]

# Media type that wraps each repo as {"starred_at": ..., "repo": {...}}
STAR_MEDIA_TYPE = "application/vnd.github.star+json"


def starred_raw(client: GitHubClient, login: str, max_pages: int = 1000) -> list[dict[str, Any]]:
    return list(
        client.paginate(f"/users/{login}/starred", max_pages=max_pages, accept=STAR_MEDIA_TYPE)
    )


def starred(client: GitHubClient, login: str, max_pages: int = 1000) -> list[Star]:
    """Every repository ``login`` has starred, newest star first."""
    return [Star.from_api(login, item) for item in starred_raw(client, login, max_pages)]
