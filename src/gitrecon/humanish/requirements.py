"""Requirement sentences of normative text: who MUST, SHOULD or MAY do what.

    find_requirements("A client MUST send the header. It MAY retry.")

Keywords are found with the lexer of ``resources/grammars/humanish/rfc2119.lark`` (capitals
only, as RFC 8174 says); each sentence holding one becomes a record with its level
(``resources/humanish.yml``: obligation, prohibition, recommendation, discouragement, permission).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from functools import cache
from typing import Any

from lark import Lark

from gitrecon.config import resource
from gitrecon.humanish.commits import meanings


@cache
def _lexer() -> Lark:
    grammar = resource("grammars", "humanish", "rfc2119.lark").read_text(encoding="utf-8")
    return Lark(grammar, parser="lalr", lexer="basic")


@dataclass
class Requirement:
    level: str  # the strongest of the sentence: obligation | prohibition | recommendation | ...
    keywords: list[str]
    sentence: str
    line: int

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def find_requirements(text: str) -> list[Requirement]:
    """Every sentence of ``text`` that holds a requirement keyword, in order."""
    levels = meanings()["requirement_levels"]
    text = text.replace("\r\n", "\n")
    found: list[Requirement] = []
    start, line, keywords = 0, None, []

    def close(end: int) -> None:
        nonlocal start, line, keywords
        if keywords:
            strongest = max(keywords, key=lambda k: (levels[k[0]]["strength"], k[0] in ("PROHIBITION", "DISCOURAGEMENT")))
            sentence = re.sub(r"\s+", " ", text[start:end]).strip()
            found.append(Requirement(levels[strongest[0]]["level"], [k[1] for k in keywords], sentence, line))
        start, line, keywords = end, None, []

    for token in _lexer().lex(text):
        if token.type == "SENTENCE_END":
            close(token.end_pos)
            continue
        if line is None:
            line = token.line
        if token.type in levels:
            keywords.append((token.type, re.sub(r"\s+", " ", token.value)))
    close(len(text))
    return found


def summarize_requirements(requirements: list[Requirement]) -> dict[str, int]:
    return dict(Counter(r.level for r in requirements).most_common())
