"""One entry of an RSS / Atom / RDF feed, normalized."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from gitrecon.models.base import Entity, parse_time


@dataclass
class FeedItem(Entity):
    kind = "feed-item"

    feed: str = ""  # feed URL
    id: str = ""  # guid / atom:id / link
    title: str = ""
    link: str | None = None
    published: datetime | None = None
    updated: datetime | None = None
    summary: str = ""
    authors: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)

    @property
    def ident(self) -> str:
        return self.id

    def to_record(self) -> dict[str, Any]:
        """Raw buffer shape (JSON-ready)."""
        data = asdict(self)
        data.pop("raw", None)
        for key in ("published", "updated"):
            data[key] = data[key].isoformat() if data[key] else None
        data["kind"] = self.kind
        return data

    @classmethod
    def from_record(cls, data: dict[str, Any]) -> FeedItem:
        return cls(
            raw=data,
            feed=data.get("feed", ""),
            id=data.get("id", ""),
            title=data.get("title", ""),
            link=data.get("link"),
            published=parse_time(data.get("published")),
            updated=parse_time(data.get("updated")),
            summary=data.get("summary", ""),
            authors=data.get("authors") or [],
            categories=data.get("categories") or [],
        )
