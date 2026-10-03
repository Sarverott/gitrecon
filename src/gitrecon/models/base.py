"""Common ground for every recognized GitHub entity."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from typing import Any, ClassVar

GITHUB = "https://github.com"
GIST = "https://gist.github.com"


def parse_time(value: str | None) -> datetime | None:
    """Parse GitHub ISO-8601 timestamps (``2026-10-03T12:00:00Z``)."""
    if not value:
        return None
    return datetime.fromisoformat(value)


def plain(value: Any) -> Any:
    """Dataclasses, lists and datetimes as JSON-ready values; ``raw`` payloads dropped."""
    if isinstance(value, Entity):
        return value.to_dict()
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: plain(getattr(value, f.name)) for f in fields(value) if f.name != "raw"}
    if isinstance(value, (list, tuple, set)):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def url_for_key(key: str) -> str | None:
    """Web address of an entity key: ``user:octocat`` -> ``https://github.com/octocat``."""
    kind, _, ident = key.partition(":")
    match kind:
        case "user" if ident.endswith("[bot]"):
            return f"{GITHUB}/apps/{ident.removesuffix('[bot]')}"
        case "user" | "org" | "repo":
            return f"{GITHUB}/{ident}"
        case "gist":
            return f"{GIST}/{ident}"
        case "star":
            return f"{GITHUB}/{ident.split('->', 1)[-1]}"
        case "rfc":
            return f"https://www.rfc-editor.org/rfc/{ident.lower()}"
    return None


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

    @property
    def html_url(self) -> str | None:
        """Where a person can see this entity in a browser (``None`` when there is no page)."""
        return self.raw.get("html_url") or url_for_key(self.key)

    def to_dict(self) -> dict[str, Any]:
        """All fields as JSON-ready values (nested entities too), without raw payloads."""
        data = {f.name: plain(getattr(self, f.name)) for f in fields(self) if f.name != "raw"}
        data["kind"] = self.kind
        return data

    def to_json(self) -> dict[str, Any]:
        """The shape printed by ``--json`` and handed to GUIs: ``to_dict()`` plus ``url``."""
        return self.to_dict() | {"url": self.html_url}
