"""Hugging Face Hub dataset sync.

Deconstructed from ``datasets/setups.ipynb``. Needs the ``dev`` dependency
group (``huggingface-hub``), imported lazily so the core tool runs without it.
"""

from __future__ import annotations

from pathlib import Path

DEFAULT_REPO_ID = "Apokryf/minimap-of-uce"
DEFAULT_LOCAL_DIR = Path("./imperialmap")


def _hub():
    import huggingface_hub

    return huggingface_hub


def login(token: str | None = None) -> None:
    _hub().login(token=token)


def download_dataset(repo_id: str = DEFAULT_REPO_ID, local_dir: Path = DEFAULT_LOCAL_DIR) -> str:
    return _hub().snapshot_download(repo_id=repo_id, repo_type="dataset", local_dir=local_dir)


def upload_dataset(local_dir: Path = DEFAULT_LOCAL_DIR, repo_id: str = DEFAULT_REPO_ID):
    return _hub().upload_folder(folder_path=local_dir, repo_id=repo_id, repo_type="dataset")


def ensure_area(name: str, local_dir: Path = DEFAULT_LOCAL_DIR) -> Path:
    """Create a sub-area of the dataset (e.g. ``store-areas``) if missing."""
    path = Path(local_dir) / name
    path.mkdir(parents=True, exist_ok=True)
    return path
