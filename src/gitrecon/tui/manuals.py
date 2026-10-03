"""The documentation in docs/, read in the terminal.

Pages are listed by section (home, glossary, guides); Obsidian ``[[wikilinks]]`` are
shown as their label and kept as links to follow (``l`` in the menu viewer).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from rich.markdown import Markdown
from rich.rule import Rule

from gitrecon.config import PROJECT_ROOT

DOCS = PROJECT_ROOT / "docs"
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]")
REFERENCE_LINK = re.compile(r"\[([^\]]+)\]\[[^\]]*\]")


def pages(docs: Path = DOCS) -> list[Path]:
    if not docs.is_dir():
        return []
    return sorted(
        p for p in docs.rglob("*.md")
        # hidden and internal folders: .venv, .obsidian, _mkdocs
        if not any(part.startswith((".", "_")) for part in p.relative_to(docs).parts[:-1])
    )


def name(page: Path, docs: Path = DOCS) -> str:
    """``glossary/raw-buffer`` - the page path without the suffix."""
    return page.relative_to(docs).with_suffix("").as_posix()


def section(page: Path, docs: Path = DOCS) -> str:
    rel = page.relative_to(docs)
    return rel.parts[0] if len(rel.parts) > 1 else "home"


def title(page: Path) -> str:
    for line in page.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return REFERENCE_LINK.sub(r"\1", line[2:]).strip()
    return page.stem


def find(query: str, docs: Path = DOCS) -> list[Path]:
    query = query.lower().removesuffix(".md").strip("/")
    all_pages = pages(docs)
    exact = [p for p in all_pages if name(p, docs).lower() == query or p.stem.lower() == query]
    return exact or [p for p in all_pages if query in name(p, docs).lower()]


def links(page: Path) -> list[str]:
    """Targets of the page's ``[[wikilinks]]``, in order of first mention."""
    return list(dict.fromkeys(m.group(1).strip() for m in WIKILINK.finditer(page.read_text(encoding="utf-8"))))


def markdown(page: Path) -> Markdown:
    text = WIKILINK.sub(lambda m: f"**{(m.group(2) or m.group(1)).strip()}**", page.read_text(encoding="utf-8"))
    return Markdown(text, code_theme="ansi_dark", hyperlinks=True)


def listing(docs: Path = DOCS) -> str:
    lines = ["gitrecon manuals (docs/) - read one: task manuals -- <page>", ""]
    current = None
    for page in pages(docs):
        if section(page, docs) != current:
            current = section(page, docs)
            lines.append(f"{current}/")
        lines.append(f"  {name(page, docs):<36} {title(page)}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    """``task manuals [-- PAGE]``: list the pages, or render one."""
    from gitrecon.tui.theme import console

    query = " ".join(argv).strip()
    if not query:
        print(listing())
        return 0
    found = find(query)
    if not found:
        print(f"no page matches {query!r}\n\n{listing()}", file=sys.stderr)
        return 1
    if len(found) > 1:
        print(f"{len(found)} pages match {query!r}:")
        for page in found:
            print(f"  {name(page):<36} {title(page)}")
        return 0
    out = console()
    page = found[0]
    with out.pager(styles=True) if out.is_terminal else _NoPager():
        out.print(Rule(f"docs/{name(page)}.md"))
        out.print(markdown(page))
        if targets := links(page):
            out.print(Rule(style="muted"))
            out.print(f"[muted]see also:[/muted] {', '.join(targets)}")
    return 0


class _NoPager:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
