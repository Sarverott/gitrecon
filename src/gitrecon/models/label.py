"""Conclusion drawn about an entity: what is happening, how sure, and why."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Label:
    name: str
    target: str  # entity key, e.g. "user:octocat"
    confidence: float = 1.0
    evidence: list[str] = field(default_factory=list)  # event / gist ids
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def __str__(self) -> str:
        return f"[{self.name}] {self.target} ({self.confidence:.2f}, {len(self.evidence)} evidence)"
