"""How commands print: text for people, ``--json`` and ``--urls`` for programs.

The rules every command follows:

- default: readable text; summaries ("-- 12 labels") go to stdout with it
- ``--json``: stdout carries only JSON - a list for listings, an object for single
  results, JSON Lines (one object per line) for streams such as ``events --watch``
- ``--urls``: stdout carries only web addresses, one per line, deduplicated in order
- in both machine modes every note, progress line and summary goes to stderr

Item shapes come from the models' ``to_json()``, so the CLI and the Python API hand
the same data to GUIs, web servers and other programs.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, TypeVar

from gitrecon.models.base import plain

T = TypeVar("T")


def add_output_flags(parser: argparse.ArgumentParser, urls: bool = True) -> argparse.ArgumentParser:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true", help="print data as JSON (stdout holds only data)")
    if urls:
        group.add_argument("--urls", action="store_true", help="print only web addresses, one per line")
    return parser


def _default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if hasattr(value, "to_json"):
        return value.to_json()
    if is_dataclass(value):
        return plain(value)
    return str(value)


def dumps(data: Any, compact: bool = False) -> str:
    if compact:
        return json.dumps(data, default=_default, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(data, default=_default, ensure_ascii=False, indent=2)


def to_json(item: Any) -> Any:
    return item.to_json() if hasattr(item, "to_json") else item


def to_url(item: Any) -> str | None:
    return getattr(item, "html_url", None)


@dataclass
class Output:
    json: bool = False
    urls: bool = False

    @classmethod
    def of(cls, args: argparse.Namespace) -> Output:
        return cls(json=getattr(args, "json", False), urls=getattr(args, "urls", False))

    @property
    def machine(self) -> bool:
        return self.json or self.urls

    def note(self, message: str) -> None:
        """Human information: stdout for people, stderr when stdout carries data."""
        print(message, file=sys.stderr if self.machine else sys.stdout)

    def listing(
        self,
        items: Iterable[T],
        text: Callable[[T], str],
        data: Callable[[T], Any] = to_json,
        url: Callable[[T], str | None] = to_url,
        summary: str | Callable[[list[T]], str] | None = None,
    ) -> list[T]:
        items = list(items)
        if self.json:
            print(dumps([data(item) for item in items]))
        elif self.urls:
            for address in dict.fromkeys(u for u in map(url, items) if u):
                print(address)
        else:
            for item in items:
                print(text(item))
        if summary:
            self.note(summary(items) if callable(summary) else summary)
        return items

    def stream(
        self,
        items: Iterable[T],
        text: Callable[[T], str],
        data: Callable[[T], Any] = to_json,
        url: Callable[[T], str | None] = to_url,
    ) -> None:
        """Items as they come: JSON Lines with ``--json``, flushed after each batch."""
        for item in items:
            if self.json:
                print(dumps(data(item), compact=True))
            elif self.urls:
                if address := url(item):
                    print(address)
            else:
                print(text(item))
        sys.stdout.flush()

    def result(self, data: Any, text: str | Callable[[], str], urls: Iterable[str] = ()) -> None:
        """One structured result (status, an update, a digest...)."""
        if self.json:
            print(dumps(data))
        elif self.urls:
            for address in dict.fromkeys(urls):
                print(address)
        else:
            print(text() if callable(text) else text)
