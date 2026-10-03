"""GitHub activity event, as served by the Events API and GH Archive."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from gitrecon.models.base import Entity, parse_time
from gitrecon.models.organization import Organization
from gitrecon.models.repository import Repository
from gitrecon.models.user import User


@dataclass
class Event(Entity):
    kind = "event"

    id: str = ""
    type: str = ""
    actor: User | None = None
    repo: Repository | None = None
    org: Organization | None = None
    payload: dict[str, Any] = field(default_factory=dict, repr=False)
    public: bool = True
    created_at: datetime | None = None

    @property
    def ident(self) -> str:
        return self.id

    @property
    def action(self) -> str | None:
        """Sub-action of the event, e.g. ``opened`` for IssuesEvent."""
        return self.payload.get("action")

    @property
    def forkee(self) -> Repository | None:
        """The newly created repository of a ForkEvent."""
        if self.type == "ForkEvent" and self.payload.get("forkee"):
            return Repository.from_api(self.payload["forkee"])
        return None

    @property
    def commit_count(self) -> int:
        if self.type != "PushEvent":
            return 0
        return self.payload.get("size") or len(self.payload.get("commits") or [])

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Event:
        return cls(
            raw=data,
            id=str(data.get("id", "")),
            type=data.get("type", ""),
            actor=User.from_api(data["actor"]) if data.get("actor") else None,
            repo=Repository.from_api(data["repo"]) if data.get("repo") else None,
            org=Organization.from_api(data["org"]) if data.get("org") else None,
            payload=data.get("payload") or {},
            public=data.get("public", True),
            created_at=parse_time(data.get("created_at")),
        )
