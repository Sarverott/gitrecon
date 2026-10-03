"""Colours and the shared console of the interactive menu."""

from __future__ import annotations

from functools import cache

from rich.console import Console
from rich.theme import Theme

THEME = Theme(
    {
        "brand": "bold red",
        "accent": "bold yellow",
        "muted": "grey58",
        "key": "bold cyan",
        "cursor": "bold black on yellow",
        "chosen": "bold green",
        "section": "bold magenta",
        "ok": "green",
        "warn": "yellow",
        "fail": "bold red",
        "url": "underline cyan",
        "cmd": "bold white on grey23",
    }
)

LOGO = "[brand]git[/brand][accent]recon[/accent]"


@cache
def console() -> Console:
    return Console(theme=THEME, highlight=False)
