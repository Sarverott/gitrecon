"""Cloning many git repositories into one folder: gists, a user's repositories, an organization's.

``clone_many()`` takes ``(name, url)`` pairs and clones each into ``<path>/<name>``. The path
is created when missing; an existing clone is left alone (or fast-forwarded with
``update=True``); one failure does not stop the rest. Credentials come from git itself
(for github.com usually ``gh auth git-credential``) - tokens never end up in a URL or in
``.git/config``.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any


def git(*args: str) -> subprocess.CompletedProcess:
    # GIT_TERMINAL_PROMPT=0: a missing or private-without-access repository fails instead of
    # waiting for a password nobody types
    env = os.environ | {"GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False, env=env)


def clone_many(
    targets: Iterable[tuple[str, str]],
    path: str | Path,
    update: bool = False,
    depth: int | None = None,
    progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    """Clone ``(name, url)`` pairs into ``<path>/<name>``; ``depth=1`` keeps only the newest commit.

    Returns ``{"name", "path", "status": "cloned" | "exists" | "updated" | "failed", "error"}``
    per target.
    """
    root = Path(path).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    items = list(targets)
    results = []
    for index, (name, url) in enumerate(items, start=1):
        target = root / name
        done = None
        if (target / ".git").is_dir():
            if update:
                done = git("-C", str(target), "pull", "--ff-only", "--quiet")
                status = "updated" if done.returncode == 0 else "failed"
            else:
                status = "exists"
        elif target.exists() and any(target.iterdir()):
            status = "failed"
        else:
            extra = ["--depth", str(depth)] if depth else []
            done = git("clone", "--quiet", *extra, url, str(target))
            status = "cloned" if done.returncode == 0 else "failed"
        error = None
        if status == "failed":
            error = done.stderr.strip() if done else f"{target} exists and is not a git clone"
        results.append({"name": name, "path": str(target), "status": status, "error": error})
        if progress:
            progress(f"{index}/{len(items)} {status:<8} {name}")
    return results
