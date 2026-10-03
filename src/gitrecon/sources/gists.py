"""Gist discovery: the public gist stream and per-user gists."""

from __future__ import annotations

from typing import Any

from gitrecon.sources.github_api import GitHubClient


def public_gists(client: GitHubClient, since: str | None = None, max_pages: int = 3) -> list[dict[str, Any]]:
    """Newest public gists across GitHub (``since`` = ISO timestamp)."""
    params = {"since": since} if since else None
    return list(client.paginate("/gists/public", params=params, max_pages=max_pages))


def user_gists(client: GitHubClient, login: str, max_pages: int = 10) -> list[dict[str, Any]]:
    return list(client.paginate(f"/users/{login}/gists", max_pages=max_pages))
