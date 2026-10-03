"""GitHub Project (Projects v2 board owned by a user or an organization)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from gitrecon.models.base import Entity, parse_time


@dataclass
class Project(Entity):
    kind = "project"

    owner: str = ""
    number: int | None = None
    id: str | None = None
    title: str | None = None
    short_description: str | None = None
    public: bool | None = None
    closed: bool | None = None
    url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def ident(self) -> str:
        return f"{self.owner.lower()}/{self.number}"

    @property
    def html_url(self) -> str | None:
        return self.url

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Project:
        """Accepts a GraphQL ``ProjectV2`` node (camelCase fields)."""
        owner = data.get("owner") or {}
        return cls(
            raw=data,
            owner=owner.get("login", ""),
            number=data.get("number"),
            id=data.get("id"),
            title=data.get("title"),
            short_description=data.get("shortDescription"),
            public=data.get("public"),
            closed=data.get("closed"),
            url=data.get("url"),
            created_at=parse_time(data.get("createdAt")),
            updated_at=parse_time(data.get("updatedAt")),
        )
