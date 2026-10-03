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

    @property
    def html_url(self) -> str | None:
        """Events have no page of their own: the repository they happened in (else the actor)."""
        if self.repo:
            return self.repo.html_url
        return self.actor.html_url if self.actor else None

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "action": self.action,
            "actor": self.actor.login if self.actor else None,
            "repo": self.repo.full_name if self.repo else None,
            "org": self.org.login if self.org else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "url": self.html_url,
            "payload": self.payload,
        }

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
