"""A commit per changed file, each message written by a local model.

    plan = plan_commits(".")          # nothing is committed: file, message, why
    apply_plan(".", plan)             # one commit per file, in the plan's order

The form the model fills in is commitizen's own: its questions (type, scope, subject,
body, breaking change, footer) become the fields of ``CommitForm``, and commitizen turns the
answers into the message - so what a person gets from ``task commit`` and what the model
writes have the same shape and pass the same check.

Two models can share the work (``reader=``): a small reasoning model first reads everything
known about the file - what gitrecon's own readers say (language, lines changed, what it
imports, who uses it) and the diff - and writes notes; the writer then fills the form from
the notes. One model alone gets the same facts and the diff directly.

Order: files other changed files import come first (the import graph of
``gitrecon.code.imports``), so every commit stands on what was committed before it; then
code, then tests, then everything else.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_DIFF_CHARS = 3000  # what a small local model reads in seconds, not minutes
SUBJECT_LIMIT = 72
TYPES = ["fix", "feat", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore"]
PATTERN = re.compile(r"(?s)(build|bump|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\(\S+\))?!?: ([^\n\r]+)((\n\n.*)|(\s*))?$")

SYSTEM = """You write git commit messages in the Conventional Commits form, one changed file at a time.
Fields:
- prefix: the type of change. feat = a new capability; fix = a defect repaired; docs = documentation only;
  style = formatting only; refactor = restructured without new behaviour; perf = faster; test = tests only;
  build = build system or dependencies; ci = CI configuration; chore = housekeeping.
- scope: one short word for the part of the project touched (a folder or module name), no spaces; may be empty.
- subject: an imperative summary of WHAT changed in this file, lower case, no full stop, at most 60 characters.
- body: one or two sentences on WHY, or empty.
- is_breaking_change: true only when users of the code must change something.
- footer: empty unless an issue is referenced.
Describe only what the diff shows. Do not invent."""


def _git(repo: Path, *args: str, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False, errors="replace",
                          env=env)
    if check and done.returncode != 0:
        raise RuntimeError(done.stderr.strip() or done.stdout.strip() or f"git {' '.join(args)} failed")
    return done


def _commitizen() -> Any:
    """Commitizen's committer for this project (its form and its message builder).

    Importing commitizen configures logging and, doing so, switches off every logger that
    exists already - gitrecon's own warnings would go silent. They are switched back on.
    """
    import logging

    loggers = [logger for logger in logging.root.manager.loggerDict.values() if isinstance(logger, logging.Logger)]
    was_on = [logger for logger in loggers if not logger.disabled]
    try:
        from commitizen import factory
        from commitizen.config import read_cfg

        return factory.committer_factory(read_cfg())
    finally:
        for logger in was_on:
            logger.disabled = False


def commit_types() -> list[str]:
    """The types commitizen offers in this project (its first question); a standard list without it."""
    try:
        question = next(q for q in _commitizen().questions() if q["name"] == "prefix")
        return [choice["value"] for choice in question["choices"]] + ["chore"]
    except Exception:  # noqa: BLE001 - commitizen is a development tool, not always installed
        return TYPES


def commit_form() -> type:
    """The pydantic model of commitizen's commit form (built on demand: pydantic comes with the llm extra)."""
    from typing import Literal

    from pydantic import BaseModel, Field

    kinds = tuple(dict.fromkeys(commit_types()))

    class CommitForm(BaseModel):
        prefix: Literal[kinds]  # type: ignore[valid-type]
        scope: str = Field(default="", description="one word, no spaces; may be empty")
        subject: str = Field(description="imperative, lower case, no full stop, at most 60 characters")
        body: str = ""
        is_breaking_change: bool = False
        footer: str = ""

    return CommitForm


def build_message(answers: dict[str, Any]) -> str:
    """The commit message for a filled-in form - by commitizen when it is there, the same shape without it."""
    scope = re.sub(r"[^\w.,/-]+", "-", str(answers.get("scope") or "").strip()).strip("-")
    subject = str(answers.get("subject") or "").strip().splitlines()[0] if answers.get("subject") else ""
    subject = subject.rstrip(". ")
    subject = (subject[:1].lower() + subject[1:])[:SUBJECT_LIMIT] or "update"
    clean = {"prefix": answers.get("prefix") or "chore", "scope": scope, "subject": subject,
             "body": str(answers.get("body") or "").strip(), "is_breaking_change": bool(answers.get("is_breaking_change")),
             "footer": str(answers.get("footer") or "").strip()}
    if clean["is_breaking_change"] and not clean["footer"]:
        clean["footer"] = clean["body"] or subject  # commitizen writes "BREAKING CHANGE: <footer>"
    try:
        if clean["prefix"] == "chore":
            raise LookupError("commitizen's form has no chore")
        message = _commitizen().message(clean)
    except Exception:  # noqa: BLE001
        head = f"{clean['prefix']}({scope}): {subject}" if scope else f"{clean['prefix']}: {subject}"
        footer = f"BREAKING CHANGE: {clean['footer']}" if clean["is_breaking_change"] else clean["footer"]
        message = "\n\n".join(part for part in (head, clean["body"], footer) if part)
    if not PATTERN.match(message):
        raise ValueError(f"not a Conventional Commit: {message.splitlines()[0]!r}")
    return message


# --- what changed, and in which order --------------------------------------------------------


@dataclass
class Change:
    path: str
    status: str  # added | modified | deleted | renamed
    old_path: str | None = None


def changed_files(repo: str | Path) -> list[Change]:
    """Every file that differs from the last commit: modified, new (untracked too), deleted, renamed."""
    root = Path(repo).expanduser()
    entries = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout.split("\0")
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
            changes.append(Change(path, "renamed", old))
        elif "D" in code:
            changes.append(Change(path, "deleted"))
        elif code == "??" or "A" in code:
            changes.append(Change(path, "added"))
        else:
            changes.append(Change(path, "modified"))
    return changes


def file_diff(repo: str | Path, change: Change, limit: int = MAX_DIFF_CHARS) -> str:
    """What the model is shown for one file: its diff against the last commit, or its beginning when new."""
    root = Path(repo).expanduser()
    if change.status == "added":
        try:
            data = (root / change.path).read_bytes()
        except OSError:
            return "(unreadable)"
        if b"\0" in data[:8000]:
            return f"(a new binary file, {len(data)} bytes)"
        text = "\n".join("+" + line for line in data.decode("utf-8", errors="replace").splitlines())
    else:
        paths = [p for p in (change.old_path, change.path) if p]
        text = _git(root, "diff", "HEAD", "--no-color", "-M", "--", *paths, check=False).stdout
    if len(text) > limit:
        text = text[:limit] + f"\n... ({len(text) - limit} more characters of this diff not shown)"
    return text or "(no textual difference)"


def _rank(path: str) -> int:
    name = path.lower()
    if re.search(r"(^|/)tests?/|(^|/)test_[^/]*$|\.test\.|\.spec\.", name):
        return 2
    if name.endswith((".md", ".rst", ".txt")) or name.startswith("docs/"):
        return 3
    return 0 if re.search(r"\.(py|js|ts|tsx|jsx|php|c|cpp|h|go|rs|rb|sh|lark)$", name) else 1


def order_changes(repo: str | Path, changes: list[Change]) -> list[Change]:
    """Files other changed files import first; then code, configuration, tests, prose - each by path."""
    import networkx as nx

    from gitrecon.code.imports import import_graph

    names = {c.path for c in changes}
    graph = nx.DiGraph()
    graph.add_nodes_from(names)
    try:
        edges = import_graph(repo, untracked=True)["edges"]  # new files are part of what is being committed
    except Exception:  # noqa: BLE001 - ordering is a nicety; without the graph the ranks still apply
        edges = []
    graph.add_edges_from((target, source) for source, target in edges if source in names and target in names)
    depth = {name: 0 for name in names}
    condensed = nx.condensation(graph)  # import cycles become one step
    for node in nx.topological_sort(condensed):
        level = max((condensed.nodes[p]["level"] + 1 for p in condensed.predecessors(node)), default=0)
        condensed.nodes[node]["level"] = level
        for member in condensed.nodes[node]["members"]:
            depth[member] = level
    return sorted(changes, key=lambda c: (_rank(c.path), depth[c.path], c.path))


# --- what is known about a file before any model reads it ------------------------------------


def file_facts(repo: str | Path, change: Change, graph: dict[str, Any] | None = None) -> dict[str, Any]:
    """Facts gitrecon's own readers have about a changed file: language, size of the change, relations."""
    from gitrecon.code.languages import detect

    root = Path(repo).expanduser()
    language = detect(Path(change.path))
    facts: dict[str, Any] = {"path": change.path, "status": change.status,
                             "language": language.name if language else None,
                             "kind": language.kind if language else None}
    stat = _git(root, "diff", "HEAD", "--numstat", "--", change.path, check=False).stdout.split()
    if len(stat) >= 2 and stat[0].isdigit() and stat[1].isdigit():
        facts["lines_added"], facts["lines_deleted"] = int(stat[0]), int(stat[1])
    elif change.status == "added":
        try:
            facts["lines_added"] = len((root / change.path).read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            pass
    if graph:
        facts["imports"] = sorted(target for source, target in graph["edges"] if source == change.path)[:12]
        users = sorted(source for source, target in graph["edges"] if target == change.path)
        facts["used_by"] = len(users)
        facts["used_by_examples"] = users[:5]
    return facts


def _facts_text(facts: dict[str, Any]) -> str:
    lines = [f"File: {facts['path']}", f"What happened: {facts['status']}"]
    if facts.get("language"):
        lines.append(f"Language: {facts['language']} ({facts['kind']})")
    if "lines_added" in facts:
        lines.append(f"Lines: +{facts['lines_added']} -{facts.get('lines_deleted', 0)}")
    if facts.get("imports"):
        lines.append("It uses these files of the project: " + ", ".join(facts["imports"]))
    if facts.get("used_by"):
        lines.append(f"It is used by {facts['used_by']} file(s) of the project, e.g. " + ", ".join(facts["used_by_examples"]))
    return "\n".join(lines)


READER_SYSTEM = """You read one changed file of a software project and take notes for the person who will write
its commit message. Say only what the facts and the diff show.
- summary: one sentence - what this change does.
- changes: the separate things that changed, each a short phrase (at most five).
- kind: the type of change (feat = new capability, fix = defect repaired, docs, style, refactor, perf, test,
  build, ci, chore).
- reason: why the change was made, if the diff shows it; else empty."""


def change_notes() -> type:
    """The shape of the reader's notes (a pydantic model)."""
    from typing import Literal

    from pydantic import BaseModel

    kinds = tuple(dict.fromkeys(commit_types()))

    class ChangeNotes(BaseModel):
        summary: str
        changes: list[str] = []
        kind: Literal[kinds]  # type: ignore[valid-type]
        reason: str = ""

    return ChangeNotes


# --- the plan ----------------------------------------------------------------------------------


def fallback_answers(change: Change) -> dict[str, Any]:
    """A message without a model: the type from where the file lives, the subject from what happened to it."""
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


def write_message(repo: str | Path, change: Change, llm: Any, model: str | None = None, reader: str | None = None,
                  graph: dict[str, Any] | None = None) -> dict[str, Any]:
    """``{"path", "status", "message", "by", "answers", "facts", "notes"}`` for one file.

    ``by`` is the model that wrote the message, or ``fallback``. With ``reader`` (a model name)
    that model reads the facts and the diff first; the writer works from its notes.
    """
    hint = fallback_answers(change)
    facts = file_facts(repo, change, graph)
    known = (_facts_text(facts) + (f"\nIt was called: {change.old_path}" if change.old_path else "")
             # "chore" is only the fallback's shrug: saying it would talk the model out of feat and fix
             + (f"\nJudging by where the file lives, the type is probably: {hint['prefix']}" if hint["prefix"] != "chore" else "")
             + (f"\nA likely scope: {hint['scope']}" if hint["scope"] else ""))
    diff = file_diff(repo, change)
    room = {"num_predict": 1500}  # room for a reasoning model that thinks whatever it is told
    notes = None
    if reader:
        try:
            notes = llm.structured(change_notes(), f"{known}\n\nThe change:\n{diff}", model=reader,
                                   system=READER_SYSTEM, options=room).model_dump()
        except Exception:  # noqa: BLE001 - without notes the writer reads the diff itself
            notes = None
    if notes:
        listed = "\n".join(f"- {item}" for item in notes["changes"])
        prompt = (f"{known}\n\nNotes of a reader who studied the change:\nSummary: {notes['summary']}\n"
                  f"Changes:\n{listed}\nKind, as the reader sees it: {notes['kind']}\nReason: {notes['reason'] or '(not shown)'}"
                  f"\n\nThe beginning of the change itself:\n{diff[:1200]}")
    else:
        prompt = f"{known}\n\nThe change:\n{diff}"
    try:
        form = llm.structured(commit_form(), prompt, model=model, system=SYSTEM, options=room)
        answers = form.model_dump()
        message, by = build_message(answers), model or llm.model
    except Exception as error:  # noqa: BLE001 - a model that fails must not stop the commit plan
        answers, by = hint | {"note": str(error)[:200]}, "fallback"
        message = build_message(hint)
    return {"path": change.path, "status": change.status, "old_path": change.old_path, "message": message, "by": by,
            "answers": answers, "facts": facts, "notes": notes}


def plan_commits(repo: str | Path, llm: Any = None, model: str | None = None, limit: int | None = None,
                 progress: Any = None, reader: str | None = None) -> list[dict[str, Any]]:
    """The plan: every changed file in commit order with its message. ``llm=None``: fallback messages only.

    ``reader``: a second model that reads each file first and hands notes to the writer.
    """
    changes = order_changes(repo, changed_files(repo))[: limit or None]
    graph = None
    if llm is not None:
        try:
            from gitrecon.code.imports import import_graph

            graph = import_graph(repo, untracked=True)
        except Exception:  # noqa: BLE001 - relations are an extra for the prompt
            graph = None
    plan = []
    for change in changes:
        if progress:
            progress(f"writing the message for {change.path}")
        if llm is None:
            plan.append({"path": change.path, "status": change.status, "old_path": change.old_path,
                         "message": build_message(fallback_answers(change)), "by": "fallback",
                         "answers": fallback_answers(change)})
        else:
            plan.append(write_message(repo, change, llm, model, reader=reader, graph=graph))
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
