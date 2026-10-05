"""The structure of Python files, through the standard ``ast`` module."""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class PyStats:
    files: int = 0
    unparsed: int = 0  # syntax errors (Python 2, templates, broken files)
    functions: int = 0
    async_functions: int = 0
    classes: int = 0
    documented: int = 0  # modules, classes and functions with a docstring
    documentable: int = 0
    imports: Counter = field(default_factory=Counter)  # top-level module -> files importing it
    decorators: Counter = field(default_factory=Counter)

    @property
    def docstring_ratio(self) -> float:
        return round(self.documented / self.documentable, 3) if self.documentable else 0.0


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Call):
        node = node.func
    try:
        return ast.unparse(node)
    except Exception:  # noqa: BLE001
        return "?"


def add_file(stats: PyStats, source: str) -> None:
    """Add one Python file's structure to ``stats`` (a file that does not parse is only counted)."""
    stats.files += 1
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        stats.unparsed += 1
        return
    stats.documentable += 1
    stats.documented += ast.get_docstring(tree) is not None
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                modules.add(node.module.split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if isinstance(node, ast.ClassDef):
                stats.classes += 1
            else:
                stats.functions += 1
                stats.async_functions += isinstance(node, ast.AsyncFunctionDef)
            stats.documentable += 1
            stats.documented += ast.get_docstring(node) is not None
            stats.decorators.update(_decorator_name(d) for d in node.decorator_list)
    stats.imports.update(modules)
