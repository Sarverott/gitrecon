"""CaptorLex, step 1: the structure of source files - functions, methods, classes - in many languages.

Syntax trees come from tree-sitter (the ``code`` extra: ``uv sync --extra code``). Which
grammar reads which language is the ``structure:`` key in ``resources/languages.yml``.
A grammar is downloaded on first use and cached by tree-sitter-language-pack; without the
extra, or without the grammar, the language is simply not read.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

TOP_NAMES = 15


def available() -> bool:
    try:
        import tree_sitter_language_pack  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass
class Structure:
    files: int = 0
    unread: int = 0  # no grammar at hand, or the parser gave up
    parse_errors: int = 0  # files whose tree holds error nodes (still read)
    kinds: Counter = field(default_factory=Counter)  # function, method, class, struct, interface ...
    names: Counter = field(default_factory=Counter)  # names of what is defined

    def to_json(self) -> dict[str, Any]:
        return {"files": self.files, "unread": self.unread, "parse_errors": self.parse_errors,
                "defined_kinds": dict(sorted(self.kinds.items())),
                "defined": [name for name, _ in self.names.most_common(TOP_NAMES)]}


def _kind(kind: Any) -> str:
    """``Function`` -> ``function``; the pack's ``{"other":"constant"}`` -> ``constant``."""
    text = str(kind)
    if text.startswith("{"):
        try:
            text = str(next(iter(json.loads(text).values())))
        except (ValueError, StopIteration):
            text = "other"
    return text.rsplit(".", 1)[-1].lower()


def _collect(items: list, stats: Structure) -> None:
    for item in items:
        stats.kinds[_kind(item.kind)] += 1
        if item.name:
            stats.names[item.name] += 1
        _collect(item.children, stats)


def add_file(stats: Structure, source: str, grammar: str) -> None:
    """Add one file's definitions to ``stats``; never raises."""
    from tree_sitter_language_pack import process
    from tree_sitter_language_pack.options import ProcessConfig

    stats.files += 1
    try:
        result = process(source, ProcessConfig(language=grammar, imports=False, exports=False))
    except Exception:  # noqa: BLE001 - a missing grammar or a parser failure is not our problem
        stats.unread += 1
        return
    stats.parse_errors += bool(getattr(result.metrics, "error_count", 0))
    _collect(result.structure, stats)
