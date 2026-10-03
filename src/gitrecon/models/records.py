"""Recognizing what a raw buffer record is."""

from __future__ import annotations

from typing import Any

from gitrecon.models.event import Event
from gitrecon.models.gist import Gist


def from_record(record: dict[str, Any]) -> Event | Gist | None:
    """Turn a raw record into its model, telling events and gists apart by shape."""
    if "type" in record and "actor" in record:
        return Event.from_api(record)
    if "files" in record and "git_pull_url" in record:
        return Gist.from_api(record)
    return None
