"""GitHub gist."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from gitrecon.models.base import Entity, parse_time


@dataclass
class GistFile:
    filename: str
    language: str | None = None
    type: str | None = None
    size: int | None = None
    raw_url: str | None = None


@dataclass
class Gist(Entity):
    kind = "gist"

    id: str = ""
    owner: str | None = None
    description: str | None = None
    public: bool | None = None
    files: list[GistFile] = field(default_factory=list)
    comments: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def ident(self) -> str:
        return self.id

    @property
    def languages(self) -> set[str]:
        return {f.language for f in self.files if f.language}

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Gist:
        owner = data.get("owner") or {}
        return cls(
            raw=data,
            id=data.get("id", ""),
            owner=owner.get("login"),
            description=data.get("description"),
            public=data.get("public"),
            files=[
                GistFile(
                    filename=name,
                    language=meta.get("language"),
                    type=meta.get("type"),
                    size=meta.get("size"),
                    raw_url=meta.get("raw_url"),
                )
                for name, meta in (data.get("files") or {}).items()
            ],
            comments=data.get("comments"),
            created_at=parse_time(data.get("created_at")),
            updated_at=parse_time(data.get("updated_at")),
        )
