"""Runtime configuration, taken from environment variables."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


def _project_root() -> Path:
    """Repository root when running from a source checkout (src/gitrecon/..), else cwd."""
    root = Path(__file__).resolve().parents[2]
    return root if (root / "pyproject.toml").exists() else Path.cwd()


PROJECT_ROOT = _project_root()


def _path_env(name: str, default: Path) -> Path:
    return Path(os.environ[name]) if os.environ.get(name) else default


def _token() -> str | None:
    """GITHUB_TOKEN / GH_TOKEN, else the GitHub CLI's login (``gh auth token``), if any."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token or os.environ.get("GITRECON_NO_GH_CLI") or not shutil.which("gh"):
        return token or None
    result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False)
    return result.stdout.strip() or None if result.returncode == 0 else None


@dataclass
class Config:
    data_dir: Path = field(default_factory=lambda: _path_env("GITRECON_DATA", PROJECT_ROOT / "data"))
    datasets_dir: Path = field(
        default_factory=lambda: _path_env("GITRECON_DATASETS", PROJECT_ROOT / "datasets")
    )
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
