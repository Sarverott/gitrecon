"""Runtime configuration, taken from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or None


@dataclass
class Config:
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("GITRECON_DATA", "data")))
    github_token: str | None = field(default_factory=_token)
    api_url: str = "https://api.github.com"
    gharchive_url: str = "https://data.gharchive.org"
    user_agent: str = "gitrecon"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def state_dir(self) -> Path:
        return self.data_dir / "state"
