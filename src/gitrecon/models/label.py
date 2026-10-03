"""Conclusion drawn about an entity: what is happening, how sure, and why."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from gitrecon.models.base import url_for_key


@dataclass
class Label:
    name: str
    target: str  # entity key, e.g. "user:octocat"
    confidence: float = 1.0
    evidence: list[str] = field(default_factory=list)  # event / gist ids
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def html_url(self) -> str | None:
        """The page of the labeled entity."""
        return url_for_key(self.target)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> dict[str, Any]:
        return self.to_dict() | {"url": self.html_url}

    def __str__(self) -> str:
        return f"[{self.name}] {self.target} ({self.confidence:.2f}, {len(self.evidence)} evidence)"
