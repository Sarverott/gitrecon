from __future__ import annotations

from datetime import datetime, timedelta, timezone
from itertools import count
from pathlib import Path

import pytest
import requests

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


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests are offline: any real HTTP request through requests fails loudly."""

    def blocked(self, method, url, *args, **kwargs):
        raise AssertionError(f"test tried to reach the network: {method} {url}")

    monkeypatch.setattr(requests.sessions.Session, "request", blocked)


@pytest.fixture(autouse=True)
def no_env_files(monkeypatch):
    """Tests never read real dotenv files (no real tokens leak into them)."""
    monkeypatch.setattr("gitrecon.config.env_files", lambda: [])


@pytest.fixture
def t0() -> datetime:
    return T0


@pytest.fixture
def minutes():
    return lambda n: T0 + timedelta(minutes=n)


class FakeResponse:
    """Just enough of ``requests.Response`` for GitHubClient and the LLM clients."""

    def __init__(self, data=None, status=200, headers=None, next_url=None):
        self._data = data
        self.status_code = status
        self.headers = headers or {}
        self.links = {"next": {"url": next_url}} if next_url else {}
        self.content = b"x" if data is not None else b""

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Serves queued responses per URL prefix and records every request."""

    def __init__(self, routes):
        self.routes = routes  # {url_prefix: [FakeResponse, ...]}
        self.calls = []
        self.headers = {}

    def _serve(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        for prefix, queue in self.routes.items():
            if url.startswith(prefix):
                return queue.pop(0) if len(queue) > 1 else queue[0]
        raise AssertionError(f"unexpected {method} {url}")

    def get(self, url, **kwargs):
        return self._serve("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self._serve("POST", url, **kwargs)


def make_repo(full_name: str, language: str = "Python", stars: int = 1, description: str = "") -> dict:
    return {
        "id": hash(full_name) & 0xFFFF,
        "full_name": full_name,
        "name": full_name.split("/")[1],
        "owner": {"login": full_name.split("/")[0]},
        "language": language,
        "stargazers_count": stars,
        "description": description,
        "topics": [],
    }
