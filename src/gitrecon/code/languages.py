"""Which language a file is written in (``resources/languages.yml``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import yaml

from gitrecon.config import resource


@dataclass(frozen=True)
class Language:
    name: str
    kind: str = "code"  # code | markup | data | prose | config
    family: str | None = None  # lexical grammar: resources/grammars/lexical/<family>.lark
    keywords: frozenset[str] = field(default_factory=frozenset)


def _keywords(values: list) -> frozenset[str]:
    """Keywords as strings - an unquoted ``true`` or ``null`` in YAML arrives as a boolean or None."""
    words: set[str] = set()
    for value in values:
        if isinstance(value, bool):
            words |= {str(value).lower(), str(value)}
        elif value is None:
            words |= {"null", "None"}
        else:
            words.add(str(value))
    return frozenset(words)


@cache
def _table() -> tuple[dict[str, Language], dict[str, Language]]:
    data = yaml.safe_load(resource("languages.yml").read_text(encoding="utf-8"))
    families = data.get("families") or {}
    by_extension: dict[str, Language] = {}
    by_filename: dict[str, Language] = {}
    for name, spec in data["languages"].items():
        family = spec.get("family")
        language = Language(name, spec.get("kind", "code"), family,
                            _keywords((families.get(family) or {}).get("keywords", [])) if family else frozenset())
        for extension in spec.get("extensions", []):
            by_extension[extension.lower()] = language
        for filename in spec.get("filenames", []):
            by_filename[filename] = language
    return by_extension, by_filename


def detect(path: Path) -> Language | None:
    """The language of a file by its name, then its extension; ``None`` when unknown."""
    by_extension, by_filename = _table()
    return by_filename.get(path.name) or by_extension.get(path.suffix.lower())


def families() -> list[str]:
    return sorted({lang.family for lang in _table()[0].values() if lang.family})
