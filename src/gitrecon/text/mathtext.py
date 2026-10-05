"""Formulas written in LaTeX read as SymPy expressions - a first, small step (``math`` extra).

    read_latex(r"\\frac{1}{2} \\pi r^2")        # pi*r**2/2
    formulas_in("the area is $$\\pi r^2$$ ...")  # every $$...$$ of a text, read

Uses SymPy's Lark-based LaTeX parser (the same Lark the other grammars use). It reads
arithmetic, fractions, roots, powers, functions, sums, integrals and equations; display
commands (``\\displaystyle``, ``\\,``) are dropped first and ``\\pi`` becomes SymPy's pi. A formula
with several readings (``\\cos t + \\sin t``: write ``\\cos(t) + \\sin(t)`` ... still two) is
reported as ambiguous rather than guessed.
Layout constructs - cases, matrices, ``\\overbrace``, ``\\stackrel`` - are not mathematics a
parser can evaluate; :func:`formulas_in` reports those as unread rather than failing.
"""

from __future__ import annotations

import re
from typing import Any

DISPLAY = re.compile(r"\\(?:displaystyle|textstyle|scriptstyle|limits|nolimits|left|right|,|;|!|quad|qquad)(?![A-Za-z])|\\ ")
DOLLARS = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
PI = "upsilon"  # the parser has no \\pi; the rarely used upsilon stands in and is put back as SymPy's pi
# (so a formula that really uses \\upsilon reads it as pi - a known limit of this first step)


def read_latex(latex: str) -> Any:
    """One formula as a SymPy expression (an ``Eq`` when it holds ``=``). Raises ``ValueError`` when unreadable."""
    try:
        import sympy
        from sympy.parsing.latex import parse_latex
    except ImportError as error:
        raise RuntimeError("reading formulas needs the math extra: uv sync --extra math") from error
    text = DISPLAY.sub(" ", latex).strip()
    text = re.sub(r"\\pi(?![A-Za-z])", rf" \\{PI} ", text)
    try:
        expression = parse_latex(text, backend="lark")
    except Exception as error:  # noqa: BLE001 - the parser raises its own family of errors
        raise ValueError(f"not readable as mathematics: {latex.strip()[:80]}") from error
    if getattr(expression, "data", None) == "_ambig":  # several readings: "\cos t + \sin t" is one sum or one cosine
        readings = "  |  ".join(str(child) for child in expression.children)
        raise ValueError(f"ambiguous: {latex.strip()[:80]}  ->  {readings}")
    if expression is None or not hasattr(expression, "subs"):
        raise ValueError(f"not readable as mathematics: {latex.strip()[:80]}")
    return expression.subs(sympy.Symbol(PI), sympy.pi)


def formulas_in(text: str) -> list[dict[str, Any]]:
    """Every ``$$...$$`` of a text: ``{"latex", "expression" (str or None), "symbols"}``."""
    found = []
    for latex in DOLLARS.findall(text):
        try:
            expression = read_latex(latex)
            found.append({"latex": latex.strip(), "expression": str(expression),
                          "symbols": sorted(str(s) for s in expression.free_symbols)})
        except ValueError as error:
            found.append({"latex": latex.strip(), "expression": None, "symbols": [],
                          "why": "ambiguous" if str(error).startswith("ambiguous") else "not mathematics a parser reads"})
    return found
