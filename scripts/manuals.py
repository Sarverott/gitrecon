"""Read the documentation in docs/ from the terminal.

    task manuals                    list every page with its title
    task manuals -- user-namespace  render one page (by file name, path, or part of either)

Obsidian [[wikilinks]] are shown as their label and listed under "see also".
Renders with rich when it is installed, else prints the markdown as it is.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]")


def pages() -> list[Path]:
    return sorted(
        p for p in DOCS.rglob("*.md")
        # hidden and internal folders: .venv, .obsidian, _mkdocs
        if not any(part.startswith((".", "_")) for part in p.relative_to(DOCS).parts[:-1])
    )


def title(page: Path) -> str:
    for line in page.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", line[2:]).strip()
    return page.stem


def find(query: str) -> list[Path]:
    query = query.lower().removesuffix(".md").strip("/")
    all_pages = pages()
    exact = [p for p in all_pages if p.relative_to(DOCS).with_suffix("").as_posix().lower() == query
             or p.stem.lower() == query]
    return exact or [p for p in all_pages if query in p.relative_to(DOCS).as_posix().lower()]


def listing() -> str:
    lines = ["gitrecon manuals (docs/) - read one: task manuals -- <page>", ""]
    section = None
    for page in pages():
        rel = page.relative_to(DOCS)
        current = rel.parts[0] if len(rel.parts) > 1 else "home"
        if current != section:
            section = current
            lines.append(f"{section}/")
        name = rel.with_suffix("").as_posix()
        lines.append(f"  {name:<36} {title(page)}")
    return "\n".join(lines)


def render(page: Path) -> None:
    text = page.read_text(encoding="utf-8")
    links = sorted({m.group(1).strip() for m in WIKILINK.finditer(text)})
    text = WIKILINK.sub(lambda m: (m.group(2) or m.group(1)).strip(), text)
    if links:
        text += "\n\n---\n\nsee also: " + ", ".join(f"`{link}`" for link in links)
    header = f"docs/{page.relative_to(DOCS).as_posix()}"
    try:
        from rich.console import Console
        from rich.markdown import Markdown
        from rich.rule import Rule
    except ImportError:
        print(f"== {header}\n\n{text}")
        return
    console = Console()
    with console.pager(styles=True) if console.is_terminal else _nullcontext():
        console.print(Rule(header))
        console.print(Markdown(text))


class _nullcontext:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def main(argv: list[str]) -> int:
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
            print(f"  {page.relative_to(DOCS).with_suffix('').as_posix():<36} {title(page)}")
        return 0
    render(found[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
