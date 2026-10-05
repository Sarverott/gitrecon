"""Saving the working tree as one commit, with the message written from what changed.

    save_message(".")     # the message, nothing committed
    save(".")             # git add -A, git commit - hooks and routines run as usual

The message is a Conventional Commit: the type is what all changed files agree on
(``docs``, ``test``, ``ci``, ``build``), else ``chore``; the subject counts the files per top
folder; the body lists them.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

SUBJECT_LIMIT = 72
BUILD_FILES = {"pyproject.toml", "uv.lock", "package.json", "package-lock.json", "Dockerfile", "compose.yaml"}
PATTERN = re.compile(r"(?s)(build|bump|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\(\S+\))?!?: ([^\n\r]+)((\n\n.*)|(\s*))?$")


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False, errors="replace")
    if check and done.returncode != 0:
        raise RuntimeError(done.stderr.strip() or done.stdout.strip() or f"git {' '.join(args)} failed")
    return done


def changed_files(repo: str | Path) -> list[tuple[str, str]]:
    """``(status, path)`` of every file that differs from the last commit: added, modified, deleted, renamed."""
    entries = _git(Path(repo).expanduser(), "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout.split("\0")
    changes, index = [], 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        if "R" in code or "C" in code:
            old = entries[index]
            index += 1
            # renamed in the index, then removed: what is left is the old file gone
            changes.append(("deleted", old) if code[1] == "D" else ("renamed", path))
        elif "D" in code:
            changes.append(("deleted", path))
        elif code == "??" or "A" in code:
            changes.append(("added", path))
        else:
            changes.append(("modified", path))
    return sorted(changes, key=lambda change: change[1])


def kind_of(path: str) -> str:
    """The commit type a file's place suggests: ``ci``, ``test``, ``docs``, ``build`` or ``chore``."""
    name = path.lower()
    if path.startswith(".github/"):
        return "ci"
    if re.search(r"(^|/)tests?/|(^|/)test_[^/]*$|\.test\.|\.spec\.", name):
        return "test"
    if name.endswith((".md", ".rst", ".txt")) or name.startswith("docs/"):
        return "docs"
    return "build" if Path(path).name in BUILD_FILES else "chore"


def save_message(repo: str | Path) -> str | None:
    """One message for everything that changed; ``None`` when nothing changed."""
    changes = changed_files(repo)
    if not changes:
        return None
    kinds = {kind_of(path) for _, path in changes}
    areas: dict[str, int] = {}
    for _, path in changes:
        top = path.split("/")[0] if "/" in path else "root"
        areas[top] = areas.get(top, 0) + 1
    ranked = sorted(areas.items(), key=lambda kv: (-kv[1], kv[0]))
    where = ", ".join(f"{name} {count}" for name, count in ranked[:3]) + (", ..." if len(ranked) > 3 else "")
    subject = f"save {len(changes)} file{'' if len(changes) == 1 else 's'} ({where})"[:SUBJECT_LIMIT]
    body = "\n".join(f"{status}: {path}" for status, path in changes[:80])
    if len(changes) > 80:
        body += f"\n... and {len(changes) - 80} more"
    message = f"{kinds.pop() if len(kinds) == 1 else 'chore'}: {subject}\n\n{body}"
    assert PATTERN.match(message), message
    return message


def save(repo: str | Path) -> dict[str, Any]:
    """Commit everything that changed as one commit. ``{"committed", "message", "sha", "error"}``."""
    root = Path(repo).expanduser()
    message = save_message(root)
    if message is None:
        return {"committed": False, "message": None, "sha": None, "error": None}
    _git(root, "add", "-A")
    result = _git(root, "commit", "-m", message, check=False)
    ok = result.returncode == 0
    return {"committed": ok, "message": message,
            "sha": _git(root, "rev-parse", "--short", "HEAD").stdout.strip() if ok else None,
            "error": None if ok else (result.stderr.strip() or result.stdout.strip())[-800:]}
