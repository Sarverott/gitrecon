"""RAT ("rattish") script builder: glossary section + sentence rebuild section.

Deconstructed from ``docs/tests-with-md-parsing-and-rattish-implementations.ipynb``
(cell 7). Output is byte-identical to the notebook for the same input.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gitrecon.text.a12y import Glossary, paratangle
from gitrecon.text.tokenizer import text_to_tokenchain_sentences

RAT_HEADER = """
@glossaries
#strmode
$WORDS
!pipe_meanings
"""

RAT_CONVERSATIONS = """
@conversations
#intmode
$spellindex
=0
#strmode
.build_sentence
$sentence
=WORDS.A12Y.
"""

RAT_SENTENCE_SEP = """
!talk_sentence
#intmode
$spellindex
+1
#strmode
.build_sentence
$sentence
=WORDS.A12Y.\n
"""

RAT_FOOTER = """
!talk_sentence
<save
"""


def spelling_rat(keystr: str, elements: list[str]) -> str:
    """One ``.a12y_entry`` block of the glossary section."""
    d = [
        ".a12y_entry",
        f"${keystr}",
        "=" + "\n+".join(elements),
        f":{'-'.join(paratangle(keystr))}",
        "*" + "\n*".join("-".join(paratangle(elem)) for elem in elements),
        "",
    ]
    return "\n".join(d)


@dataclass
class RatBuild:
    script: str
    glossary: Glossary = field(default_factory=Glossary)

    @property
    def lines(self) -> int:
        return len(self.script.split("\n"))


def build_rat(raw_text: str, glossary: Glossary | None = None) -> RatBuild:
    glossary = Glossary() if glossary is None else glossary
    sentences = [
        "\n+".join(glossary.a12y(word) for word in sentence)
        for sentence in text_to_tokenchain_sentences(raw_text)
    ]
    script = RAT_HEADER
    for keyword, words in glossary.items():
        script += spelling_rat(keyword, words)
    script += RAT_CONVERSATIONS
    script += RAT_SENTENCE_SEP.join(sentences)
    script += RAT_FOOTER
    return RatBuild(script=script, glossary=glossary)
