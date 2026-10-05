import pytest
from conftest import FIXTURES

from gitrecon.text.a12y import Glossary, a12y_key, check_a12y, paratangle
from gitrecon.text.jsonlark import parse_json_tree
from gitrecon.text.markdown import md_to_text, render_toc
from gitrecon.text.rat import build_rat
from gitrecon.text.tokenizer import (
    sentence_prep,
    sentence_prep_legacy,
    text_to_tokenchain_sentences,
)


def test_sentence_prep_spells_symbols_and_digits():
    assert sentence_prep("Run: task 2") == ["run", "DWUKROP", "task", "DWA"]


def test_sentence_prep_legacy_collapses_brackets():
    assert sentence_prep_legacy("f{x}") == ["f", "BRACKETSTART", "x", "BRACKETSTOP"]


def test_text_to_sentences_splits_on_dots_and_lines():
    assert text_to_tokenchain_sentences("one two. three\nfour") == [["one", "two"], ["three"], ["four"]]


def test_a12y_numeronyms():
    assert a12y_key("workflows") == "w9s"
    assert a12y_key("a") == "a1a"
    assert a12y_key("_x") == "0-5f-2-78"
    assert check_a12y("ok") and not check_a12y("1x") and not check_a12y("")
    with pytest.raises(ValueError):
        a12y_key("")


def test_glossary_collisions_and_expand():
    glossary = Glossary()
    assert glossary.a12y("cross") == "c5s"
    assert glossary.a12y("codes") == "c5s1"
    assert glossary.a12y("cross") == "c5s"
    assert glossary == {"c5s": ["cross", "codes"]}
    assert glossary.expand("c5s1") == "codes"
    assert glossary.expand("c5s") == "cross"


def test_paratangle_is_stable():
    assert paratangle("task") == ["44801b4", "527edb25"]


def test_rat_matches_original_notebook_output():
    md_text = (FIXTURES / "taskfile-llms.md").read_text(encoding="utf-8")
    expected = (FIXTURES / "taskfile-llms.rat").read_text(encoding="utf-8")
    build = build_rat(md_to_text(md_text))
    assert build.script == expected
    assert build.lines == 1283
    assert build.glossary["c5s"] == ["cross", "codes"]


def test_json_lark_parses():
    tree = parse_json_tree('{"a": [1, true, null]}')
    assert tree.data == "value"


def test_render_toc():
    toc = render_toc("# Hello\n\n## World\n")
    assert 'href="#hello"' in toc and 'href="#world"' in toc


def test_latex_formulas_as_sympy():
    sympy = pytest.importorskip("sympy")
    pytest.importorskip("lark")
    from gitrecon.text.mathtext import formulas_in, read_latex

    assert read_latex(r"\sqrt{x+3}") == sympy.sqrt(sympy.Symbol("x") + 3)
    area = read_latex(r"\displaystyle \frac{1}{2} \pi r^2\,")
    assert area == sympy.pi * sympy.Symbol("r") ** 2 / 2 and area.subs("r", 2) == 2 * sympy.pi
    assert read_latex("a + b = c") == sympy.Eq(sympy.Symbol("a") + sympy.Symbol("b"), sympy.Symbol("c"))
    assert str(read_latex(r"\int_0^1 x^2 dx")) == "Integral(x**2, (x, 0, 1))"
    with pytest.raises(ValueError, match="ambiguous"):
        read_latex(r"\cos(t)+\sin(t)")
    found = formulas_in(r'A["$$x^2$$"] --> B("$$\overbrace{a+b}^{\text{note}}$$") --> C("$$\pi r^2$$")')
    assert [(f["expression"], f["symbols"]) for f in found] == [("x**2", ["x"]), (None, []), ("pi*r**2", ["r"])]
    assert found[1]["why"] == "not mathematics a parser reads"
