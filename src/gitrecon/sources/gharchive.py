"""GH Archive (gharchive.org): every public GitHub event, one gzip JSONL file per hour.

Files are streamed straight to disk - never held in memory - and kept in their
original gzip form, which is also the raw buffer format.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from gitrecon.config import Config

log = logging.getLogger(__name__)

CHUNK = 1 << 20  # 1 MiB


def parse_hour(spec: str) -> datetime:
    """``2026-10-03-15`` (GH Archive naming) or ``2026-10-03T15`` -> UTC hour."""
    spec = spec.replace("T", "-")
    day, _, hour = spec.rpartition("-")
    return datetime.strptime(day, "%Y-%m-%d").replace(hour=int(hour), tzinfo=timezone.utc)


def hour_range(start: datetime, end: datetime) -> Iterator[datetime]:
    """Every hour from ``start`` to ``end`` inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(hours=1)


def archive_name(hour: datetime) -> str:
    # GH Archive does not zero-pad the hour: 2015-01-01-15, 2015-01-01-3
    return f"{hour:%Y-%m-%d}-{hour.hour}.json.gz"


def download_hour(hour: datetime, dest: Path, config: Config | None = None, overwrite: bool = False) -> Path:
    config = config or Config()
    if dest.exists() and not overwrite:
        log.info("already have %s", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{config.gharchive_url}/{archive_name(hour)}"
    partial = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=120, headers={"User-Agent": config.user_agent}) as r:
        r.raise_for_status()
        with partial.open("wb") as fh:
            for chunk in r.iter_content(CHUNK):
                fh.write(chunk)
    partial.rename(dest)
    log.info("downloaded %s (%d bytes)", dest, dest.stat().st_size)
    return dest
