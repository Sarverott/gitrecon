"""Rendering collected data as compact text lines a model can read."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path

from gitrecon.models import Label, Star
from gitrecon.sources.links import Link


def star_lines(stars: Iterable[Star]) -> Iterator[str]:
    for star in stars:
        repo = star.repo
        when = f"{star.starred_at:%Y-%m-%d}" if star.starred_at else "?"
        topics = f" #{' #'.join(repo.topics)}" if repo.topics else ""
        desc = (repo.description or "").replace("\n", " ")[:200]
        yield f"{repo.full_name} [{repo.language or '-'}] *{repo.stargazers_count or 0} starred {when}: {desc}{topics}"


def label_lines(labels: Iterable[Label]) -> Iterator[str]:
    for label in labels:
        details = {k: v for k, v in label.details.items() if k not in ("from", "to")}
        yield f"{label.name} {label.target} confidence={label.confidence} {json.dumps(details, default=str)}"


def link_lines(links: Iterable[Link]) -> Iterator[str]:
    for link in links:
        yield f"{link.kind} {link.url}"


def file_lines(path: Path) -> Iterator[str]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield line.rstrip("\n")
