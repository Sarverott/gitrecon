"""Gists: the public gist stream, a user's gists, a user's gist catalog, and cloning them.

``gist_catalog()`` describes every gist of a user (GraphQL for files, sizes, stars, forks
and comments - 100 gists per request; REST for commit counts, one request each).
``clone_gists()`` clones them as they are, one folder per gist id, from
``https://gist.github.com/<gistID>.git``.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from gitrecon.sources.github_api import GitHubClient

GIST_CLONE_URL = "https://gist.github.com/{gist_id}.git"
PRIVACY = ("public", "all", "secret")

_GIST_FIELDS = """
  totalCount
  pageInfo { hasNextPage endCursor }
  nodes {
    name description isPublic stargazerCount createdAt updatedAt
    files(limit: 300) { name size }
    forks { totalCount }
    comments { totalCount }
  }
"""
USER_GISTS = f"""query($login: String!, $after: String) {{
  user(login: $login) {{ gists(first: 100, after: $after, privacy: PUBLIC,
    orderBy: {{field: CREATED_AT, direction: ASC}}) {{ {_GIST_FIELDS} }} }}
}}"""
VIEWER_GISTS = f"""query($privacy: GistPrivacy!, $after: String) {{
  viewer {{ login gists(first: 100, after: $after, privacy: $privacy,
    orderBy: {{field: CREATED_AT, direction: ASC}}) {{ {_GIST_FIELDS} }} }}
}}"""


def public_gists(client: GitHubClient, since: str | None = None, max_pages: int = 3) -> list[dict[str, Any]]:
    """Newest public gists across GitHub (``since`` = ISO timestamp)."""
    params = {"since": since} if since else None
    return list(client.paginate("/gists/public", params=params, max_pages=max_pages))


def user_gists(client: GitHubClient, login: str, max_pages: int = 10) -> list[dict[str, Any]]:
    return list(client.paginate(f"/users/{login}/gists", max_pages=max_pages))


def gist_catalog(
    username: str,
    client: GitHubClient | None = None,
    privacy: str = "public",
    with_commits: bool = True,
    progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    """Every gist of ``username``, oldest first, as::

        {"gistID", "filelist", "description", "stars", "comments", "forks", "commits",
         "size", "public", "created_at", "url"}

    ``privacy="all"`` / ``"secret"`` include secret gists - GitHub shows those only to their
    owner, so the token must belong to ``username``. ``with_commits=False`` skips the one
    REST request per gist that counts commits (``commits`` is then ``None``).
    ``size`` is the sum of the files' sizes in bytes (a clone also carries history).
    """
    if privacy not in PRIVACY:
        raise ValueError(f"privacy must be one of {PRIVACY}")
    client = client or GitHubClient()
    nodes: list[dict[str, Any]] = []
    after = None
    while True:
        if privacy == "public":
            page = client.graphql(USER_GISTS, {"login": username, "after": after})["user"]
            if page is None:
                raise LookupError(f"no GitHub user {username!r}")
        else:
            page = client.graphql(VIEWER_GISTS, {"privacy": privacy.upper(), "after": after})["viewer"]
            if page["login"].lower() != username.lower():
                raise PermissionError(f"secret gists of {username} need {username}'s token, not {page['login']}'s")
        gists = page["gists"]
        nodes += gists["nodes"]
        if not gists["pageInfo"]["hasNextPage"]:
            break
        after = gists["pageInfo"]["endCursor"]

    catalog = []
    for index, node in enumerate(nodes, start=1):
        gist_id = node["name"]
        commits = None
        if with_commits:
            commits = client.count(f"/gists/{gist_id}/commits")
            if progress:
                progress(f"commits counted: {index}/{len(nodes)}")
        catalog.append({
            "gistID": gist_id,
            "filelist": [f["name"] for f in node.get("files") or []],
            "description": node.get("description") or "",
            "stars": node.get("stargazerCount", 0),
            "comments": (node.get("comments") or {}).get("totalCount", 0),
            "forks": (node.get("forks") or {}).get("totalCount", 0),
            "commits": commits,
            "size": sum(f.get("size") or 0 for f in node.get("files") or []),
            "public": node.get("isPublic", True),
            "created_at": node.get("createdAt"),
            "url": f"https://gist.github.com/{gist_id}",
        })
    return catalog


def clone_url(gist_id: str, pattern: str = GIST_CLONE_URL) -> str:
    return pattern.format(gist_id=gist_id)


def clone_gists(
    gists: Iterable[dict[str, Any] | str],
    path: str | Path,
    update: bool = False,
    pattern: str = GIST_CLONE_URL,
    progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    """Clone gists (catalog entries or plain ids) into ``path``/<gistID>, as they are.

    ``path`` is created when missing. An existing clone is left alone, or fast-forwarded
    with ``update=True``. One failure does not stop the rest. Returns one entry per gist:
    ``{"gistID", "path", "status": "cloned" | "exists" | "updated" | "failed", "error"}``.
    """
    root = Path(path).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    results = []
    items = list(gists)
    for index, gist in enumerate(items, start=1):
        gist_id = gist if isinstance(gist, str) else gist["gistID"]
        target = root / gist_id
        if (target / ".git").is_dir():
            if update:
                done = _git("-C", str(target), "pull", "--ff-only", "--quiet")
                status = "updated" if done.returncode == 0 else "failed"
            else:
                done, status = None, "exists"
        elif target.exists() and any(target.iterdir()):
            done, status = None, "failed"
        else:
            done = _git("clone", "--quiet", clone_url(gist_id, pattern), str(target))
            status = "cloned" if done.returncode == 0 else "failed"
        error = None
        if status == "failed":
            error = done.stderr.strip() if done else f"{target} exists and is not a git clone"
        results.append({"gistID": gist_id, "path": str(target), "status": status, "error": error})
        if progress:
            progress(f"{index}/{len(items)} {status:<8} {gist_id}")
    return results


def _git(*args: str) -> subprocess.CompletedProcess:
    # GIT_TERMINAL_PROMPT=0: a deleted gist must fail, not ask for a password
    env = os.environ | {"GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False, env=env)
