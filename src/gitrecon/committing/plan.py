"""The plan of commits - one per changed file - and carrying it out.

    plan = plan_commits(".")                      # nothing is committed: file, message, who answered
    apply_plan(".", plan)                         # one commit per file, in the plan's order

Who writes the messages is a handler (``gitrecon.committing.handlers``); the planner only
gathers the changes, orders them, asks the handler, and makes sure every step ends with a
valid message.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from gitrecon.committing.changes import _git, changed_files, file_facts, order_changes
from gitrecon.committing.form import build_message, form_fields
from gitrecon.committing.handlers import HANDLERS, ChangeContext, Handler, path_handler


def plan_commits(repo: str | Path, handler: Handler | str = "path", limit: int | None = None,
                 progress: Any = None) -> list[dict[str, Any]]:
    """Every changed file in commit order, each with its message.

    A step: ``{"path", "status", "old_path", "message", "by", "answers", "facts"}``; ``by`` is the
    handler's name, or ``path`` with a ``note`` when the chosen handler did not give a usable answer.
    """
    root = Path(repo).expanduser()
    name = handler if isinstance(handler, str) else getattr(handler, "__name__", "handler")
    ask = HANDLERS[handler] if isinstance(handler, str) else handler
    changes = order_changes(root, changed_files(root))[: limit or None]
    graph = None
    if changes and ask is not path_handler:  # relations are for handlers that read; the plain one does not
        try:
            from gitrecon.code.imports import import_graph

            graph = import_graph(root, untracked=True)
        except Exception:  # noqa: BLE001 - an extra, never a reason to fail
            graph = None
    fields = form_fields() if changes else []
    plan = []
    for position, change in enumerate(changes):
        if progress:
            progress(f"{position + 1}/{len(changes)} {change.path}")
        context = ChangeContext(root, change, file_facts(root, change, graph), fields, position, len(changes))
        answers, by, note = None, name, None
        try:
            answers = ask(context)
            message = build_message(answers) if answers else None
        except Exception as error:  # noqa: BLE001 - a handler that fails must not stop the plan
            message, note = None, str(error)[:200]
        if message is None:
            answers, by = path_handler(context), "path"
            message = build_message(answers)
            note = note or (f"{name} passed" if ask is not path_handler else None)
        plan.append({"path": change.path, "status": change.status, "old_path": change.old_path, "message": message,
                     "by": by, "answers": answers, "facts": context.facts} | ({"note": note} if note else {}))
    return plan


def apply_plan(repo: str | Path, plan: list[dict[str, Any]], progress: Any = None) -> list[dict[str, Any]]:
    """Commit the plan, one file per commit. Stops at the first commit that fails (a hook, a check).

    The BOS routines that act on the whole tree are switched off for the series
    (``BOS_SKIP_ROUTINES=add-all,push``): a per-file commit must not stage everything, and
    the branch is pushed once at the end by whoever runs this, not after every file.
    """
    root = Path(repo).expanduser()
    env = os.environ | {"BOS_SKIP_ROUTINES": "add-all,push"}
    done = []
    for step in plan:
        paths = [p for p in (step.get("old_path"), step["path"]) if p]
        _git(root, "add", "-A", "--", *paths, env=env)
        result = _git(root, "commit", "--only", "-m", step["message"], "--", *paths, check=False, env=env)
        ok = result.returncode == 0
        done.append(step | {"committed": ok, "sha": _git(root, "rev-parse", "--short", "HEAD").stdout.strip() if ok else None,
                            "error": None if ok else (result.stderr.strip() or result.stdout.strip())[-600:]})
        if progress:
            progress(f"{'committed' if ok else 'FAILED   '} {step['path']}")
        if not ok:
            _git(root, "reset", "-q", "--", *paths, check=False)  # leave the file changed but unstaged
            break
    return done


def save_message(repo: str | Path) -> str | None:
    """One message for everything that changed, written from the paths alone; ``None`` when nothing changed.

    The type is what all files agree on (``docs``, ``test``, ``ci``, ``build``), else ``chore``;
    the subject counts the files per top folder; the body lists them.
    """
    root = Path(repo).expanduser()
    changes = changed_files(root)
    if not changes:
        return None
    context = lambda change: ChangeContext(root, change)  # noqa: E731
    kinds = {path_handler(context(change))["prefix"] for change in changes}
    areas: dict[str, int] = {}
    for change in changes:
        top = change.path.split("/")[0] if "/" in change.path else "root"
        areas[top] = areas.get(top, 0) + 1
    where = ", ".join(f"{name} {count}" for name, count in sorted(areas.items(), key=lambda kv: (-kv[1], kv[0]))[:3])
    if len(areas) > 3:
        where += ", ..."
    files = "file" if len(changes) == 1 else "files"
    body = "\n".join(f"{change.status}: {change.path}" for change in sorted(changes, key=lambda c: c.path)[:80])
    if len(changes) > 80:
        body += f"\n... and {len(changes) - 80} more"
    return build_message({"prefix": kinds.pop() if len(kinds) == 1 else "chore",
                          "subject": f"save {len(changes)} {files} ({where})", "body": body})


def save(repo: str | Path) -> dict[str, Any]:
    """Commit everything that changed as one commit with :func:`save_message`. Hooks and routines run as usual."""
    root = Path(repo).expanduser()
    message = save_message(root)
    if message is None:
        return {"committed": False, "message": None, "error": None}
    _git(root, "add", "-A")
    result = _git(root, "commit", "-m", message, check=False)
    ok = result.returncode == 0
    return {"committed": ok, "message": message, "sha": _git(root, "rev-parse", "--short", "HEAD").stdout.strip() if ok else None,
            "error": None if ok else (result.stderr.strip() or result.stdout.strip())[-800:],
            "hooks": (result.stdout + result.stderr).strip()[-400:] if ok else None}
