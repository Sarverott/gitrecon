"""Lexical statistics of source files, with Lark lexers from ``resources/grammars/lexical``.

One grammar per language *family* names what a comment, a string, a number and a name look
like; anything else is an ``OTHER`` token, so lexing never fails on unfamiliar syntax. From
the tokens: code and comment lines, the names used (keywords left out), and the URLs found in
strings and comments.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from functools import cache

from lark import Lark

from gitrecon.code.languages import Language
from gitrecon.config import resource

URL = re.compile(r"""https?://[^\s<>"'`\])|\\]+""")
MIN_NAME = 3  # shorter names (i, x, id) say little


@cache
def lexer(family: str) -> Lark:
    grammar = resource("grammars", "lexical", f"{family}.lark").read_text(encoding="utf-8")
    return Lark(grammar, parser="lalr", lexer="basic")


@dataclass
class LexStats:
    lines: int = 0
    blank: int = 0
    code: int = 0
    comment: int = 0
    tokens: Counter = field(default_factory=Counter)  # by type: COMMENT, STRING, NUMBER, NAME, OTHER
    names: Counter = field(default_factory=Counter)
    urls: list[str] = field(default_factory=list)

    def add(self, other: LexStats) -> None:
        self.lines += other.lines
        self.blank += other.blank
        self.code += other.code
        self.comment += other.comment
        self.tokens.update(other.tokens)
        self.names.update(other.names)
        self.urls += other.urls

    @property
    def comment_ratio(self) -> float:
        """Comment lines per line that has code or comment."""
        total = self.code + self.comment
        return round(self.comment / total, 3) if total else 0.0


def lex(text: str, language: Language) -> LexStats:
    """Statistics of one file's text; ``language.family`` picks the grammar."""
    all_lines = text.split("\n")
    if all_lines and all_lines[-1] == "":
        all_lines.pop()
    stats = LexStats(lines=len(all_lines), blank=sum(1 for line in all_lines if not line.strip()))
    code_lines: set[int] = set()
    comment_lines: set[int] = set()
    for token in lexer(language.family).lex(text):
        stats.tokens[token.type] += 1
        span = range(token.line, (token.end_line or token.line) + 1)
        if token.type == "COMMENT":
            comment_lines.update(span)
            stats.urls += URL.findall(token.value)
        else:
            code_lines.update(span)
            if token.type == "NAME":
                if len(token.value) >= MIN_NAME and token.value not in language.keywords:
                    stats.names[token.value] += 1
            elif token.type == "STRING":
                stats.urls += URL.findall(token.value)
    stats.code = len(code_lines)
    stats.comment = len(comment_lines - code_lines)  # a line with code and a comment counts as code
    return stats
