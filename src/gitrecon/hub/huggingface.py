"""Hugging Face Hub dataset sync for the map (``Apokryf/minimap-of-uce``).

Deconstructed from ``datasets/setups.ipynb``. The notebook ran from ``datasets/``,
so its ``./imperialmap`` is ``<project>/datasets/imperialmap`` - now resolved from
the project root (override with ``GITRECON_DATASETS``), not from the working dir.

Needs ``huggingface-hub`` (dev dependency group), imported lazily.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from gitrecon.config import Config

DEFAULT_REPO_ID = "Apokryf/minimap-of-uce"
MAP_DIRNAME = "imperialmap"


def _hub():
    import huggingface_hub

    return huggingface_hub


def default_local_dir(config: Config | None = None) -> Path:
    return (config or Config()).datasets_dir / MAP_DIRNAME


def login(token: str | None = None) -> None:
    _hub().login(token=token)


@dataclass
class MapDataset:
    repo_id: str = DEFAULT_REPO_ID
    local_dir: Path = field(default_factory=default_local_dir)

    def pull(self) -> Path:
        """Download (or refresh) the dataset snapshot into ``local_dir``."""
        _hub().snapshot_download(repo_id=self.repo_id, repo_type="dataset", local_dir=self.local_dir)
        return self.local_dir

    def push(self, message: str, create_pr: bool = False):
        """Upload ``local_dir`` as one commit (or as a pull request on the Hub)."""
        return _hub().upload_folder(
            folder_path=self.local_dir,
            repo_id=self.repo_id,
            repo_type="dataset",
            commit_message=message,
            create_pr=create_pr,
            ignore_patterns=[".cache/**"],
        )

    def ensure_area(self, name: str) -> Path:
        """Create a sub-area of the map (e.g. ``store-areas``) if missing."""
        path = self.local_dir / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def areas(self) -> list[str]:
        if not self.local_dir.exists():
            return []
        return sorted(p.name for p in self.local_dir.iterdir() if p.is_dir() and not p.name.startswith("."))

    def files(self) -> list[Path]:
        if not self.local_dir.exists():
            return []
        return sorted(
            p for p in self.local_dir.rglob("*")
            if p.is_file() and ".cache" not in p.relative_to(self.local_dir).parts
        )
