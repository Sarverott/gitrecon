"""Repositories and organizations of a user, and cloning them in bulk.

    user_repos("sarverott")                 # repositories the user owns
    user_orgs("sarverott")                  # organizations the user belongs to
    org_repos("The-Apokryf")                # repositories of an organization
    clone_user_repos("sarverott")           # -> ~/__WORKSHOP/forge/sarverott/<name>
    clone_org_repos("The-Apokryf")          # -> ~/__WORKSHOP/forge/The-Apokryf/<name>, or give a path

Listings are plain dicts (``repo_entry``); clones go to ``<path>/<name>`` through
``cloning.clone_many``. What GitHub shows depends on the token: private repositories and
private organization memberships only to their owner / members.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from gitrecon.sources.cloning import clone_many, default_clone_path
from gitrecon.sources.github_api import GitHubClient

PRIVACY = ("public", "all")
MAX_PAGES = 1000


def repo_entry(data: dict[str, Any]) -> dict[str, Any]:
    """One repository, as listings return it (GitHub's ``size`` is in KiB)."""
    return {
        "name": data["name"],
        "full_name": data["full_name"],
        "owner": (data.get("owner") or {}).get("login"),
        "url": data.get("html_url") or f"https://github.com/{data['full_name']}",
        "clone_url": data.get("clone_url") or f"https://github.com/{data['full_name']}.git",
        "description": data.get("description") or "",
        "language": data.get("language"),
        "topics": data.get("topics") or [],
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "size_kib": data.get("size", 0),
        "fork": bool(data.get("fork")),
        "archived": bool(data.get("archived")),
        "private": bool(data.get("private")),
        "default_branch": data.get("default_branch"),
        "created_at": data.get("created_at"),
        "pushed_at": data.get("pushed_at"),
    }


def viewer_login(client: GitHubClient) -> str | None:
    """Whose token this is (``None`` without one)."""
    if not client.config.github_token:
        return None
    return (client.get("/user").data or {}).get("login")


def _is_viewer(client: GitHubClient, username: str) -> bool:
    login = viewer_login(client)
    return bool(login) and login.lower() == username.lower()


def _filtered(items: Iterable[dict[str, Any]], include_forks: bool, include_archived: bool) -> list[dict[str, Any]]:
    entries = [repo_entry(item) for item in items]
    return [r for r in entries if (include_forks or not r["fork"]) and (include_archived or not r["archived"])]


def user_repos(
    username: str,
    client: GitHubClient | None = None,
    privacy: str = "public",
    include_forks: bool = True,
    include_archived: bool = True,
) -> list[dict[str, Any]]:
    """Repositories ``username`` owns, oldest first.

    ``privacy="all"`` adds private ones - only with ``username``'s own token.
    """
    if privacy not in PRIVACY:
        raise ValueError(f"privacy must be one of {PRIVACY}")
    client = client or GitHubClient()
    params = {"sort": "created", "direction": "asc"}
    if privacy == "all":
        if not _is_viewer(client, username):
            raise PermissionError(f"private repositories of {username} need {username}'s token")
        items = client.paginate("/user/repos", {**params, "affiliation": "owner", "visibility": "all"},
                                max_pages=MAX_PAGES)
    else:
        items = client.paginate(f"/users/{username}/repos", {**params, "type": "owner"}, max_pages=MAX_PAGES)
    return _filtered(items, include_forks, include_archived)


def user_orgs(username: str, client: GitHubClient | None = None) -> list[dict[str, Any]]:
    """Organizations ``username`` belongs to.

    With ``username``'s own token every membership; otherwise only the public ones.
    """
    client = client or GitHubClient()
    path = "/user/orgs" if _is_viewer(client, username) else f"/users/{username}/orgs"
    return [
        {"login": org["login"], "url": f"https://github.com/{org['login']}", "description": org.get("description") or ""}
        for org in client.paginate(path, max_pages=MAX_PAGES)
    ]


def org_repos(
    org: str,
    client: GitHubClient | None = None,
    include_forks: bool = True,
    include_archived: bool = True,
) -> list[dict[str, Any]]:
    """Repositories of an organization, oldest first (private ones too, for its members)."""
    client = client or GitHubClient()
    items = client.paginate(f"/orgs/{org}/repos", {"type": "all", "sort": "created", "direction": "asc"},
                            max_pages=MAX_PAGES)
    return _filtered(items, include_forks, include_archived)


def clone_repos(
    repos: Iterable[dict[str, Any]],
    path: str | Path,
    update: bool = False,
    depth: int | None = None,
    progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    """Clone listed repositories into ``<path>/<name>``.

    Returns ``{"full_name", "path", "status": "cloned" | "exists" | "updated" | "failed", "error"}``.
    ``depth=1`` takes only the newest commit (much smaller; no history).
    """
    repos = list(repos)
    results = clone_many(((r["name"], r["clone_url"]) for r in repos), path, update=update, depth=depth,
                         progress=progress)
    return [{"full_name": repo["full_name"], **{k: v for k, v in result.items() if k != "name"}}
            for repo, result in zip(repos, results)]


def clone_user_repos(username: str, path: str | Path | None = None, client: GitHubClient | None = None,
                     privacy: str = "public", include_forks: bool = True, include_archived: bool = True,
                     **clone_options: Any) -> list[dict[str, Any]]:
    """Every repository ``username`` owns, cloned into ``<path>/<name>``.

    Without ``path``: ``<forge>/<username>/`` (``~/__WORKSHOP/forge/<username>/``).
    """
    repos = user_repos(username, client, privacy, include_forks, include_archived)
    return clone_repos(repos, path or default_clone_path(username), **clone_options)


def clone_org_repos(org: str, path: str | Path | None = None, client: GitHubClient | None = None,
                    include_forks: bool = True, include_archived: bool = True,
                    **clone_options: Any) -> list[dict[str, Any]]:
    """Every repository of an organization, cloned into ``<path>/<name>``.

    Without ``path``: ``<forge>/<org>/`` (``~/__WORKSHOP/forge/<org>/``).
    """
    repos = org_repos(org, client, include_forks, include_archived)
    return clone_repos(repos, path or default_clone_path(org), **clone_options)
