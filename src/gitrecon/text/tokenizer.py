"""Word-chain tokenizer: symbols are spelled out as uppercase word tokens.

Deconstructed from the first notebook, ``docs/tests-with-md-parsing-and-rattish-implementations.ipynb``
(removed, see git history; demo: ``examples/text-experiments``)
(cells 5 and 6).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

# Polish spelling table (cell 6). Order matters: replacements run top to bottom.
REPLACE_MATRIX: dict[str, str] = {
    "0": "ZERO",
    "1": "JEDEN",
    "2": "DWA",
    "3": "TRZY",
    "4": "CZTERY",
    "5": "PIECI",
    "6": "SZESCI",
    "7": "SIEDEM",
    "8": "OSIEM",
    "9": "DZIEWIECI",
    ",": "PRZECINEK",
    "-": "DASZ",
    ":": "DWUKROP",
    ";": "SEPARATOR",
    "#": "HASZTAG",
    '"': "SKOKPRZECIN SKOKPRZECIN",
    "`": "SKOKPRZECIN",
    "'": "SKOKPRZECIN",
    "\t": "TAB",
    "\r": "WRACAJ",
    "[": "STARTNAWIAS",
    "{": "STARTNAWIAS",
    "(": "STARTNAWIAS",
    "]": "STOPNAWIAS",
    "}": "STOPNAWIAS",
    ")": "STOPNAWIAS",
    "\\": "SLESZ",
    "/": "SLESZ",
    "@": "MAUPA",
    "&": "AMPERSAND",
    "|": "PIPE",
    "~": "LAMBDA",
    "*": "ASTERISK",
    "^": "UPINDEX",
    "%": "PERCENT",
    "$": "DOLARSIGN",
    "!": "SHOUT",
    "?": "QUESTION",
    "=": "EQUALS",
    ".": "END",
    "+": "PLUS",
    "_": "FLOOR",
    ">": "GREATER",
    "<": "LESSER",
}


def _split_words(wordline: str) -> list[str]:
    return [x.strip() for x in wordline.split(" ") if x.strip()]


def sentence_prep(wordline: str, matrix: Mapping[str, str] = REPLACE_MATRIX) -> list[str]:
    """Lowercase a sentence and spell out every symbol from ``matrix``."""
    wordline = wordline.lower()
    for replacer, word in matrix.items():
        wordline = wordline.replace(replacer, f" {word} ")
    return _split_words(wordline)


def sentence_prep_legacy(wordline: str) -> list[str]:
    """First, English variant of :func:`sentence_prep` (cell 5).

    Kept for comparison: quotes collapse into ``UPPERCOMMA`` and every bracket
    kind collapses into ``BRACKETSTART`` / ``BRACKETSTOP``; digits stay as-is.
    """
    wordline = wordline.lower()
    wordline = wordline.replace(",", " COMMA ")
    wordline = wordline.replace(":", " DASH ")
    wordline = wordline.replace(";", " SEPARATOR ")
    wordline = wordline.replace("#", " HASHTAG ")
    wordline = wordline.replace('"', "''").replace("`", "'").replace("'", " UPPERCOMMA ")
    wordline = wordline.replace("\t", " TAB ")
    wordline = wordline.replace("\r", " RETURN ")
    wordline = wordline.replace("[", "(").replace("{", "(").replace("(", " BRACKETSTART ")
    wordline = wordline.replace("]", ")").replace("}", ")").replace(")", " BRACKETSTOP ")
    wordline = wordline.replace("\\", "/").replace("/", " SLASH ")
    wordline = wordline.replace("@", " AT ")
    wordline = wordline.replace("&", " AMPERSAND ")
    wordline = wordline.replace("|", " PIPE ")
    wordline = wordline.replace("~", " LAMBDA ")
    wordline = wordline.replace("*", " ASTERISK ")
    wordline = wordline.replace("^", " UPINDEX ")
    wordline = wordline.replace("%", " PERCENT ")
    wordline = wordline.replace("$", " DOLARSIGN ")
    wordline = wordline.replace("!", " SHOUT ")
    wordline = wordline.replace("?", " QUESTION ")
    wordline = wordline.replace("=", " EQUALS ")
    wordline = wordline.replace(".", " END ")
    wordline = wordline.replace("+", " PLUS ")
    wordline = wordline.replace("_", " FLOOR ")
    wordline = wordline.replace(">", " GREATER ")
    wordline = wordline.replace("<", " LESSER ")
    return _split_words(wordline)


def text_to_tokenchain_sentences(
    textstr: str,
    prep: Callable[[str], list[str]] = sentence_prep,
) -> list[list[str]]:
    """Split text into sentences (on ``.`` and newlines) and tokenize each one."""
    sentences = textstr.replace(".", "\n").split("\n")
    return [prep(sentence.strip()) for sentence in sentences if sentence.strip()]
