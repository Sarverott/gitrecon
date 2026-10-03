"""Common ground for every recognized GitHub entity."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, ClassVar


def parse_time(value: str | None) -> datetime | None:
    """Parse GitHub ISO-8601 timestamps (``2026-10-03T12:00:00Z``)."""
    if not value:
        return None
    return datetime.fromisoformat(value)


@dataclass
class Entity:
    """Anything gitrecon can map: it has a kind and a stable key in the graph."""

    kind: ClassVar[str] = "entity"

    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def ident(self) -> str:
        raise NotImplementedError

    @property
    def key(self) -> str:
        """Graph node key, e.g. ``user:octocat`` or ``repo:octocat/hello``."""
        return f"{self.kind}:{self.ident}"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("raw", None)
        data["kind"] = self.kind
        return data
