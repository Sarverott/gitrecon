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


def forge_dir() -> Path:
    """The forge of the active BOS workshop: where cloned work goes by default.

    ``GITRECON_FORGE`` if set; else ``forge/`` of the nearest ``__WORKSHOP`` above the
    project (the active workshop); else ``~/__WORKSHOP/forge``.
    """
    if os.environ.get("GITRECON_FORGE"):
        return Path(os.environ["GITRECON_FORGE"]).expanduser()
    for parent in PROJECT_ROOT.parents:
        if parent.name == "__WORKSHOP":
            return parent / "forge"
    return Path.home() / "__WORKSHOP" / "forge"


def env_files() -> list[Path]:
    """Dotenv files to read, most specific first.

    ``GITRECON_ENV_FILE`` if set, the project's own ``.env``, then the BOS forge
    ``.env`` (``__WORKSHOP/forge/.env``, found by walking up from the project).
    TODO: the forge-level .env is a temporary home for secrets (HF_TOKEN, GH_TOKEN);
    move them to .BOS/setup/ tokens once BOS manages them.
    """
    files = []
    if os.environ.get("GITRECON_ENV_FILE"):
        files.append(Path(os.environ["GITRECON_ENV_FILE"]))
    files.append(PROJECT_ROOT / ".env")
    for parent in PROJECT_ROOT.parents:
        if parent.name == "forge" and parent.parent.name == "__WORKSHOP":
            files.append(parent / ".env")
            break
    return files


def parse_env(text: str) -> dict[str, str]:
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        values[key.strip()] = value.strip().strip("'\"")
    return values


def load_env() -> list[Path]:
    """Load dotenv files into ``os.environ`` without overriding what is already set."""
    loaded = []
    for path in env_files():
        if path.is_file():
            for key, value in parse_env(path.read_text(encoding="utf-8")).items():
                os.environ.setdefault(key, value)
            loaded.append(path)
    return loaded


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

    @property
    def links_catalog(self) -> Path:
        """The link catalog harvested from gists (``gitrecon links --save``)."""
        return self.data_dir / "catalog" / "links.jsonl"
