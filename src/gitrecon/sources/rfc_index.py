"""RFC Editor index (``rfc-index.txt``) parser.

Ported from gist ``c21ec17ac458228b3a0da27ee56c12af`` (rfc_index_parsing). The index
format moved on since that notebook: numbers are no longer zero-padded (``1 Host
Software``, ``RFC1``) and RFCs above 9999 exist, so every pattern here takes any
number of digits; multi-word statuses (``PROPOSED STANDARD``) are kept whole.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

import requests

from gitrecon.models.rfc import RFC

INDEX_URL = "https://www.rfc-editor.org/rfc-index.txt"

# The entries follow the second "RFC INDEX" banner (the first one heads the preamble).
BANNER = re.compile(r"^\s+RFC INDEX\n\s+-+\n", re.MULTILINE)
ENTRY_START = re.compile(r"^(\d+) ", re.MULTILINE)

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE = re.compile(rf"\b((?:{MONTHS}) \d{{4}})\.")
FORMATS = re.compile(r"\(Format: ([^)]*)\)")
STATUS = re.compile(r"\(Status: ([^)]*)\)")
DOI = re.compile(r"\(DOI: ([^)]*)\)")
FIELD_START = re.compile(r" \((?:Format:|Status:|DOI:|Obsoletes |Obsoleted by |Updates |Updated by |Also )")
MENTION = re.compile(r"\b(RFC\d+)\b")
RELATION = {
    "obsoletes": re.compile(r"\(Obsoletes ([^)]*)\)"),
    "obsoleted_by": re.compile(r"\(Obsoleted by ([^)]*)\)"),
    "updates": re.compile(r"\(Updates ([^)]*)\)"),
    "updated_by": re.compile(r"\(Updated by ([^)]*)\)"),
    "also": re.compile(r"\(Also ([^)]*)\)"),
}


def fetch_index(url: str = INDEX_URL, timeout: float = 120) -> str:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def unwrap(block: str) -> str:
    """Join an entry's wrapped lines; a line ending in ``-`` continues the same word."""
    out = ""
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        if not out:
            out = line
        elif out.endswith("-"):
            out += line
        else:
            out += " " + line
    return out


def entry_blocks(text: str) -> Iterator[str]:
    banners = list(BANNER.finditer(text))
    body = text[banners[-1].end():] if banners else text
    starts = [m.start() for m in ENTRY_START.finditer(body)]
    for start, end in zip(starts, starts[1:] + [len(body)]):
        yield body[start:end]


def _split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _authors(text: str) -> list[str]:
    """``J. Mandel, Ed., S. Turner`` -> ``["J. Mandel, Ed.", "S. Turner"]``."""
    names: list[str] = []
    for part in _split_list(text):
        if part.rstrip(".") in {"Ed", "Eds"} and names:
            names[-1] += f", {part.rstrip('.')}."
        else:
            names.append(part)
    return names


def parse_entry(block: str) -> RFC:
    line = unwrap(block)
    number_text, _, rest = line.partition(" ")
    number = int(number_text)
    if rest.strip() == "Not Issued.":
        return RFC(number=number, title="Not Issued", not_issued=True, description=line)

    # title, authors and date come before the first known parenthesised field;
    # a plain " (" is not enough, titles have parentheses too ("CMS (CMC)")
    fields = FIELD_START.search(rest)
    head = rest[: fields.start()] if fields else rest
    date_match = DATE.search(head)
    title, _, after_title = head.partition(". ")
    authors_text = after_title[: after_title.find(date_match.group(1))] if date_match else after_title
    rfc = RFC(
        number=number,
        title=title.strip(),
        authors=_authors(authors_text.strip().rstrip(".")),
        date=date_match.group(1) if date_match else None,
        description=line,
    )
    if m := FORMATS.search(rest):
        rfc.formats = [f.lower() for f in _split_list(m.group(1))]
    if m := STATUS.search(rest):
        rfc.status = " ".join(m.group(1).split())
    if m := DOI.search(rest):
        rfc.doi = m.group(1).strip()
    for attr, pattern in RELATION.items():
        if m := pattern.search(rest):
            setattr(rfc, attr, _split_list(m.group(1)))
    own = f"RFC{number}"
    rfc.related = sorted({r for r in MENTION.findall(rest) if r != own}, key=lambda r: int(r[3:]))
    return rfc


def parse_index(text: str) -> list[RFC]:
    return [parse_entry(block) for block in entry_blocks(text)]
