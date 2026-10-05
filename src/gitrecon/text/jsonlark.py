"""JSON grammar for Lark, used to inspect raw API responses as a parse tree.

The grammar lives in ``resources/grammars/json.lark``, with the other grammars. Deconstructed
from the first notebook (cell 9; removed, see git history; demo: ``examples/text-experiments``).
For bulk data use ``json`` - this is for tree-level exploration.
"""

from __future__ import annotations

from functools import cache

from lark import Lark, Tree

from gitrecon.config import resource


@cache
def json_parser() -> Lark:
    return Lark(resource("grammars", "json.lark").read_text(encoding="utf-8"), start="value")


def parse_json_tree(text: str) -> Tree:
    return json_parser().parse(text)
