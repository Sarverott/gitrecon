"""GitHub user account (also the ``actor`` of an event)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from gitrecon.models.base import GITHUB, Entity, parse_time


@dataclass
class User(Entity):
    kind = "user"

    login: str = ""
    id: int | None = None
    type: str = "User"
    name: str | None = None
    company: str | None = None
    location: str | None = None
    email: str | None = None
    followers: int | None = None
    following: int | None = None
    public_repos: int | None = None
    public_gists: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def ident(self) -> str:
        return self.login.lower()

    @property
    def html_url(self) -> str:
        if self.raw.get("html_url"):
            return self.raw["html_url"]
        if self.login.endswith("[bot]"):  # bots are GitHub Apps
            return f"{GITHUB}/apps/{self.login.removesuffix('[bot]')}"
        return f"{GITHUB}/{self.login}"

    @property
    def is_bot(self) -> bool:
        return self.type == "Bot" or self.login.endswith("[bot]")

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> User:
        """Accepts both the short event ``actor`` and the full ``/users/{u}`` payload."""
        return cls(
            raw=data,
            login=data.get("login", ""),
            id=data.get("id"),
            type=data.get("type", "User"),
            name=data.get("name"),
            company=data.get("company"),
            location=data.get("location"),
            email=data.get("email"),
            followers=data.get("followers"),
            following=data.get("following"),
            public_repos=data.get("public_repos"),
            public_gists=data.get("public_gists"),
            created_at=parse_time(data.get("created_at")),
            updated_at=parse_time(data.get("updated_at")),
        )
