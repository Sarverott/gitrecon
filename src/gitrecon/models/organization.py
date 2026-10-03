"""GitHub organization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from gitrecon.models.base import GITHUB, Entity, parse_time


@dataclass
class Organization(Entity):
    kind = "org"

    login: str = ""
    id: int | None = None
    name: str | None = None
    description: str | None = None
    blog: str | None = None
    location: str | None = None
    is_verified: bool | None = None
    public_repos: int | None = None
    followers: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def ident(self) -> str:
        return self.login.lower()

    @property
    def html_url(self) -> str:
        return self.raw.get("html_url") or f"{GITHUB}/{self.login}"

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Organization:
        """Accepts both the short event ``org`` and the full ``/orgs/{o}`` payload."""
        return cls(
            raw=data,
            login=data.get("login", ""),
            id=data.get("id"),
            name=data.get("name"),
            description=data.get("description"),
            blog=data.get("blog"),
            location=data.get("location"),
            is_verified=data.get("is_verified"),
            public_repos=data.get("public_repos"),
            followers=data.get("followers"),
            created_at=parse_time(data.get("created_at")),
            updated_at=parse_time(data.get("updated_at")),
        )
