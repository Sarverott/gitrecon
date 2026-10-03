"""Numeronym ("a12y"-style) word abbreviation with a collision glossary.

``workflows`` -> ``w9s``; words sharing a numeronym get an index suffix
(``cross`` -> ``c5s``, ``codes`` -> ``c5s1``). Words not bounded by ASCII
letters get a hex form ``0-<first>-<len>-<last>``.

Deconstructed from the first notebook, ``docs/tests-with-md-parsing-and-rattish-implementations.ipynb``
(removed, see git history; demo: ``examples/text-experiments``)
(cell 7). The module-level ``glossary`` global became :class:`Glossary`.
"""

from __future__ import annotations

import re
import zlib

_ASCII_LETTER = re.compile("[a-zA-Z]")


def paratangle(data: str) -> list[str]:
    """Pair of checksums (adler32, crc32) as hex strings."""
    raw = data.encode("utf-8")
    return [hex(zlib.adler32(raw))[2:], hex(zlib.crc32(raw))[2:]]


def check_a12y(testdata: str) -> bool:
    """True when the word starts and ends with an ASCII letter."""
    return bool(testdata) and bool(
        _ASCII_LETTER.match(testdata[0]) and _ASCII_LETTER.match(testdata[-1])
    )


def a12y_key(input_str: str) -> str:
    """Numeronym of a single word, without the collision index."""
    if not input_str:
        raise ValueError("cannot abbreviate an empty string")
    if check_a12y(input_str):
        return f"{input_str[0]}{len(input_str)}{input_str[-1]}"
    return "-".join(
        ["0", hex(ord(input_str[0]))[2:], hex(len(input_str))[2:], hex(ord(input_str[-1]))[2:]]
    )


class Glossary(dict[str, list[str]]):
    """Numeronym -> list of words that collide on it, in order of first sight."""

    def a12y(self, input_str: str) -> str:
        """Abbreviate a word, registering it in the glossary."""
        keystr = a12y_key(input_str)
        words = self.setdefault(keystr, [])
        if input_str not in words:
            words.append(input_str)
        index = words.index(input_str)
        return keystr if index == 0 else f"{keystr}{index}"

    def expand(self, token: str) -> str:
        """Reverse of :meth:`a12y` for a token produced by this glossary."""
        if token in self:
            return self[token][0]
        for keystr in sorted(self, key=len, reverse=True):
            suffix = token[len(keystr):]
            if token.startswith(keystr) and suffix.isdigit():
                return self[keystr][int(suffix)]
        raise KeyError(token)
