"""The commit form and the message built from it.

The form is commitizen's own - what ``task commit`` asks a person: ``prefix`` (the type),
``scope``, ``subject``, ``body``, ``is_breaking_change``, ``footer``. A handler answers it
with a plain dict; :func:`build_message` turns the answers into a Conventional Commit, by
commitizen when it is installed and in the same shape without it.
"""

from __future__ import annotations

import re
from typing import Any

SUBJECT_LIMIT = 72
TYPES = ["fix", "feat", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore"]
FIELDS = ["prefix", "scope", "subject", "body", "is_breaking_change", "footer"]
PATTERN = re.compile(r"(?s)(build|bump|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\(\S+\))?!?: ([^\n\r]+)((\n\n.*)|(\s*))?$")


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


def form_fields() -> list[dict[str, Any]]:
    """The form as data: ``{"name", "kind", "choices", "question"}`` per field, in asking order.

    From commitizen's questions when it is installed (so a project's own types show up),
    else the standard form. What a handler needs to know to answer.
    """
    try:
        questions = _commitizen().questions()
    except Exception:  # noqa: BLE001
        questions = []
    if questions:
        return [{"name": q["name"], "kind": {"list": "choice", "confirm": "yes/no"}.get(q["type"], "text"),
                 "choices": [c["value"] for c in q.get("choices", [])] + (["chore"] if q["name"] == "prefix" else []),
                 "question": str(q.get("message", "")).strip()} for q in questions]
    kinds = {"prefix": "choice", "is_breaking_change": "yes/no"}
    return [{"name": name, "kind": kinds.get(name, "text"), "choices": TYPES if name == "prefix" else [],
             "question": ""} for name in FIELDS]


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
