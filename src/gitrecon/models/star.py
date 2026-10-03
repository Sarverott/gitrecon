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

    @property
    def html_url(self) -> str:
        return self.repo.html_url

    def to_json(self) -> dict[str, Any]:
        """Flat: one starred repository per object (``repo`` is ``owner/name``)."""
        return {
            "user": self.user,
            "repo": self.repo.full_name,
            "url": self.html_url,
            "starred_at": self.starred_at.isoformat() if self.starred_at else None,
            "language": self.repo.language,
            "stars": self.repo.stargazers_count,
            "description": self.repo.description,
            "topics": self.repo.topics or [],
        }

    @classmethod
    def from_api(cls, user: str, data: dict[str, Any]) -> Star:
        """Accepts ``/users/{u}/starred`` items, plain or ``star+json`` (``{starred_at, repo}``)."""
        if "repo" in data and "starred_at" in data:
            return cls(raw=data, user=user, repo=Repository.from_api(data["repo"]),
                       starred_at=parse_time(data["starred_at"]))
        return cls(raw=data, user=user, repo=Repository.from_api(data))
