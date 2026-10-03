"""Building blocks of the menu: a selectable list, a scrolling viewer, and prompts.

``Selector`` and ``Viewer`` keep their state apart from drawing: ``handle(key)``
changes state, ``render(height)`` draws it, ``run()`` connects both to a terminal.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console, ConsoleOptions, Group, RenderableType, RenderResult
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.segment import Segment
from rich.table import Table
from rich.text import Text

from gitrecon.tui import keys
from gitrecon.tui.theme import LOGO, console

DONE, CANCEL = "done", "cancel"


@dataclass
class Item:
    label: str
    value: Any = None
    hint: str = ""
    section: str = ""

    def matches(self, needle: str) -> bool:
        haystack = f"{self.section} {self.label} {self.hint}".lower()
        return all(word in haystack for word in needle.lower().split())


@dataclass
class Selector:
    """A list chosen from with the arrows; typing filters it; space marks items in ``multi`` mode."""

    title: str
    items: list[Item]
    multi: bool = False
    subtitle: str = ""
    cursor: int = 0
    query: str = ""
    marked: set[int] = field(default_factory=set)  # indexes into items

    def visible(self) -> list[tuple[int, Item]]:
        return [(i, item) for i, item in enumerate(self.items) if not self.query or item.matches(self.query)]

    def current(self) -> Item | None:
        shown = self.visible()
        return shown[self.cursor][1] if shown else None

    def result(self) -> Any:
        if self.multi:
            return [self.items[i].value for i in sorted(self.marked)]
        item = self.current()
        return item.value if item else None

    def handle(self, key: str, page: int = 10) -> str | None:
        shown = len(self.visible())
        moves = {keys.UP: -1, keys.DOWN: 1, keys.PAGE_UP: -page, keys.PAGE_DOWN: page,
                 keys.HOME: -10**9, keys.END: 10**9}
        if key in moves:
            self.cursor = max(0, min(shown - 1, self.cursor + moves[key])) if shown else 0
        elif key == keys.ENTER:
            if self.multi or shown:
                return DONE
        elif key == keys.ESCAPE:
            if not self.query:
                return CANCEL
            self.query, self.cursor = "", 0
        elif key == keys.BACKSPACE:
            self.query, self.cursor = self.query[:-1], 0
        elif key == keys.SPACE and self.multi:
            if (picked := self.visible()[self.cursor:self.cursor + 1]):
                self.marked ^= {picked[0][0]}
        elif key == keys.SPACE:
            self.query += " "
        elif len(key) == 1 and key.isprintable():
            self.query, self.cursor = self.query + key, 0
        return None

    def render(self, height: int = 24) -> RenderableType:
        shown = self.visible()
        room = max(3, height - 7)
        top = min(max(0, self.cursor - room // 2), max(0, len(shown) - room))
        table = Table.grid(padding=(0, 1), expand=True)
        table.add_column(width=2)
        table.add_column(ratio=2, no_wrap=True)
        table.add_column(ratio=3, no_wrap=True, style="muted")
        section = None
        for row, (index, item) in enumerate(shown[top:top + room], start=top):
            if item.section and item.section != section:
                section = item.section
                table.add_row("", Text(f"── {section}", style="section"), "")
            mark = ("[chosen]●[/chosen]" if index in self.marked else "○") if self.multi else ""
            style = "cursor" if row == self.cursor else ""
            table.add_row(Text.from_markup(mark), Text(item.label, style=style or "default"), item.hint)
        if not shown:
            table.add_row("", Text("nothing matches", style="warn"), "")
        filter_line = Text.assemble(("filter: ", "muted"), (self.query or "type to filter", "accent" if self.query else "muted"))
        help_keys = "↑↓ move · enter choose · esc back" + (" · space mark" if self.multi else "")
        footer = Text(f"{help_keys} · {len(shown)}/{len(self.items)}", style="muted")
        head = [Text.from_markup(self.subtitle), Text("")] if self.subtitle else []
        return Panel(Group(*head, filter_line, Text(""), table), title=Text.from_markup(f"{LOGO} · {self.title}"),
                     subtitle=footer, subtitle_align="left", border_style="red")

    def run(self, out: Console | None = None) -> Any:
        """Show it full-screen until enter (returns the choice) or escape (returns ``None``)."""
        out = out or console()
        with Live(self.render(out.height), console=out, screen=True, auto_refresh=False) as live:
            while True:
                state = self.handle(keys.read_key(), page=max(1, out.height - 8))
                if state == DONE:
                    return self.result()
                if state == CANCEL:
                    return None
                live.update(self.render(out.height), refresh=True)


class _Lines:
    """Pre-rendered lines as a renderable (a window of a longer document)."""

    def __init__(self, lines: Sequence[list[Segment]]):
        self.lines = lines

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        for line in self.lines:
            yield from line
            yield Segment.line()


@dataclass
class Viewer:
    """A scrolling view of any renderable (markdown, JSON, tables); extra keys go back to the caller."""

    title: str
    body: RenderableType
    extra_keys: dict[str, str] = field(default_factory=dict)  # key -> what it does, shown in the footer
    offset: int = 0
    _lines: list[list[Segment]] | None = None

    def layout(self, out: Console) -> list[list[Segment]]:
        if self._lines is None:
            options = out.options.update(width=max(20, out.width - 4))
            self._lines = out.render_lines(self.body, options, pad=False)
        return self._lines

    def handle(self, key: str, height: int, total: int) -> str | None:
        page = max(1, height - 4)
        moves = {keys.UP: -1, keys.DOWN: 1, keys.PAGE_UP: -page, keys.PAGE_DOWN: page, keys.SPACE: page,
                 keys.HOME: -10**9, keys.END: 10**9}
        if key in moves:
            self.offset = max(0, min(max(0, total - page), self.offset + moves[key]))
        elif key in (keys.ESCAPE, keys.ENTER, "q"):
            return CANCEL
        elif key in self.extra_keys:
            return key
        return None

    def render(self, out: Console) -> RenderableType:
        lines = self.layout(out)
        room = max(1, out.height - 4)
        window = lines[self.offset:self.offset + room]
        shown_to = min(len(lines), self.offset + room)
        extra = "".join(f" · {k} {what}" for k, what in self.extra_keys.items())
        footer = Text(f"↑↓ pgup pgdn scroll · q back{extra} · {shown_to}/{len(lines)}", style="muted")
        return Panel(_Lines(window), title=Text.from_markup(f"{LOGO} · {self.title}"), subtitle=footer,
                     subtitle_align="left", border_style="red", height=out.height)

    def run(self, out: Console | None = None) -> str | None:
        """Show until q/esc/enter (returns ``None``) or one of ``extra_keys`` (returns that key)."""
        out = out or console()
        with Live(self.render(out), console=out, screen=True, auto_refresh=False) as live:
            while True:
                state = self.handle(keys.read_key(), out.height, len(self.layout(out)))
                if state == CANCEL:
                    return None
                if state:
                    return state
                live.update(self.render(out), refresh=True)


# --- prompts (normal screen) ------------------------------------------------------


def ask_text(label: str, default: str | None = None, required: bool = False) -> str:
    while True:
        answer = Prompt.ask(f"[accent]{label}[/accent]", default=default or "", console=console(),
                            show_default=bool(default))
        if answer or not required:
            return answer
        console().print("[warn]a value is needed here[/warn]")


def ask_int(label: str, default: int | None = None) -> int | None:
    if default is None:
        answer = Prompt.ask(f"[accent]{label}[/accent] (number, empty to skip)", default="", console=console())
        return int(answer) if answer.strip().lstrip("-").isdigit() else None
    return IntPrompt.ask(f"[accent]{label}[/accent]", default=default, console=console())


def ask_yes(label: str, default: bool = False) -> bool:
    return Confirm.ask(f"[accent]{label}[/accent]", default=default, console=console())


def choose(title: str, options: Iterable[str | tuple[str, Any, str]], subtitle: str = "") -> Any:
    """Shortcut: pick one of plain strings or ``(label, value, hint)`` tuples."""
    items = [Item(o, o) if isinstance(o, str) else Item(*o) for o in options]
    return Selector(title, items, subtitle=subtitle).run()


def wait_key(message: str = "press any key to return to the menu") -> str:
    console().print(f"\n[muted]{message}[/muted]")
    return keys.read_key()

