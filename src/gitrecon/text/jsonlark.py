"""JSON grammar for Lark, used to inspect raw API responses as a parse tree.

Deconstructed from ``docs/tests-with-md-parsing-and-rattish-implementations.ipynb``
(cell 9). For bulk data use ``json`` - this is for tree-level exploration.
"""

from __future__ import annotations

from functools import cache

from lark import Lark, Tree

JSON_GRAMMAR = r"""
    value: dict
         | list
         | ESCAPED_STRING
         | SIGNED_NUMBER
         | "true" | "false" | "null"

    list : "[" [value ("," value)*] "]"

    dict : "{" [pair ("," pair)*] "}"
    pair : ESCAPED_STRING ":" value

    %import common.ESCAPED_STRING
    %import common.SIGNED_NUMBER
    %import common.WS
    %ignore WS
"""


@cache
def json_parser() -> Lark:
    return Lark(JSON_GRAMMAR, start="value")


def parse_json_tree(text: str) -> Tree:
    return json_parser().parse(text)
