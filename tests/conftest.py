from __future__ import annotations

from datetime import datetime, timedelta, timezone
from itertools import count
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
T0 = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)

_ids = count(1_000_000)


def make_event(
    type: str = "PushEvent",
    actor: str = "alice",
    repo: str = "alice/tool",
    at: datetime = T0,
    org: str | None = None,
    payload: dict | None = None,
) -> dict:
    event = {
        "id": str(next(_ids)),
        "type": type,
        "actor": {"id": hash(actor) & 0xFFFF, "login": actor, "url": f"https://api.github.com/users/{actor}"},
        "repo": {"id": hash(repo) & 0xFFFF, "name": repo, "url": f"https://api.github.com/repos/{repo}"},
        "payload": payload or {},
        "public": True,
        "created_at": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if org:
        event["org"] = {"id": hash(org) & 0xFFFF, "login": org}
    return event


def make_gist(owner: str = "alice", at: datetime = T0, filename: str = "x.py", language: str = "Python") -> dict:
    gist_id = f"{next(_ids):x}"
    return {
        "id": gist_id,
        "git_pull_url": f"https://gist.github.com/{gist_id}.git",
        "owner": {"login": owner},
        "description": "",
        "public": True,
        "files": {filename: {"filename": filename, "language": language, "size": 10}},
        "created_at": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@pytest.fixture
def t0() -> datetime:
    return T0


@pytest.fixture
def minutes():
    return lambda n: T0 + timedelta(minutes=n)
