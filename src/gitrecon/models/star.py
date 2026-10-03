"""A star: one user starring one repository, at a known time."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from gitrecon.models.base import Entity, parse_time
from gitrecon.models.repository import Repository


@dataclass
class Star(Entity):
    kind = "star"

    user: str = ""
    repo: Repository = field(default_factory=Repository)
    starred_at: datetime | None = None

    @property
    def ident(self) -> str:
        return f"{self.user.lower()}->{self.repo.ident}"

    @classmethod
    def from_api(cls, user: str, data: dict[str, Any]) -> Star:
        """Accepts ``/users/{u}/starred`` items, plain or ``star+json`` (``{starred_at, repo}``)."""
        if "repo" in data and "starred_at" in data:
            return cls(raw=data, user=user, repo=Repository.from_api(data["repo"]),
                       starred_at=parse_time(data["starred_at"]))
        return cls(raw=data, user=user, repo=Repository.from_api(data))
