"""Commit handlers: who answers the commit form for one changed file.

A handler is any callable ``handler(context) -> answers``:

- it receives a :class:`ChangeContext` - the change, the facts known about the file, its
  diff (read only when asked for), and the form's fields;
- it returns the answers as a dict with the form's keys (``prefix``, ``scope``, ``subject``,
  ``body``, ``is_breaking_change``, ``footer`` - missing ones are taken as empty), or
  ``None`` to pass.

When a handler passes, raises, or answers something that is not a valid message, the
planner falls back to :func:`path_handler`, so a plan is always complete.

``HANDLERS`` is the registry the command line reads (``gitrecon commit-files --handler NAME``).
Today it holds only ``path``. The next approaches go here: write the function, add it with
:func:`register`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

from gitrecon.committing.changes import Change, _rank, file_diff


@dataclass
class ChangeContext:
    """Everything a handler may use to describe one change."""

    repo: Path
    change: Change
    facts: dict[str, Any] = field(default_factory=dict)  # changes.file_facts: language, lines, imports, used_by
    form: list[dict[str, Any]] = field(default_factory=list)  # form.form_fields: the questions to answer
    position: int = 0  # place in the plan, from 0
    total: int = 1

    @cached_property
    def diff(self) -> str:
        """The diff against the last commit (the whole of it; cut it down yourself if you must)."""
        return file_diff(self.repo, self.change, limit=0)


Handler = Callable[[ChangeContext], dict[str, Any] | None]
HANDLERS: dict[str, Handler] = {}


def register(name: str) -> Callable[[Handler], Handler]:
    """Decorator: make a handler choosable by name."""
    def add(handler: Handler) -> Handler:
        HANDLERS[name] = handler
        return handler
    return add


@register("path")
def path_handler(context: ChangeContext) -> dict[str, Any]:
    """The plain handler: the type from where the file lives, the subject from what happened to it."""
    change = context.change
    path = change.path
    rank = _rank(path)
    prefix = ("ci" if path.startswith(".github/") else "test" if rank == 2 else "docs" if rank == 3
              else "build" if Path(path).name in ("pyproject.toml", "uv.lock", "package.json", "package-lock.json",
                                                  "Dockerfile", "compose.yaml") else "chore")
    verb = {"added": "add", "deleted": "remove", "renamed": "rename", "modified": "update"}[change.status]
    parts = Path(path).parts
    scope = parts[-2] if len(parts) > 1 else ""
    return {"prefix": prefix, "scope": scope, "subject": f"{verb} {Path(path).name}", "body": "",
            "is_breaking_change": False, "footer": ""}
