"""GitHub repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from gitrecon.models.base import Entity, parse_time


@dataclass
class Repository(Entity):
    kind = "repo"

    full_name: str = ""
    id: int | None = None
    description: str | None = None
    fork: bool | None = None
    parent: str | None = None
    language: str | None = None
    topics: list[str] | None = None
    stargazers_count: int | None = None
    forks_count: int | None = None
    open_issues_count: int | None = None
    default_branch: str | None = None
    archived: bool | None = None
    created_at: datetime | None = None
    pushed_at: datetime | None = None

    @property
    def ident(self) -> str:
        return self.full_name.lower()

    @property
    def owner(self) -> str:
        return self.full_name.split("/", 1)[0]

    @property
    def name(self) -> str:
        return self.full_name.split("/", 1)[-1]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Repository:
        """Accepts the short event ``repo`` (``name`` = ``owner/repo``) and full repo payloads."""
        parent = data.get("parent") or data.get("source")
        return cls(
            raw=data,
            full_name=data.get("full_name") or data.get("name", ""),
            id=data.get("id"),
            description=data.get("description"),
            fork=data.get("fork"),
            parent=parent.get("full_name") if parent else None,
            language=data.get("language"),
            topics=data.get("topics"),
            stargazers_count=data.get("stargazers_count"),
            forks_count=data.get("forks_count"),
            open_issues_count=data.get("open_issues_count"),
            default_branch=data.get("default_branch"),
            archived=data.get("archived"),
            created_at=parse_time(data.get("created_at")),
            pushed_at=parse_time(data.get("pushed_at")),
        )
