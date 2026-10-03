"""Append-only raw buffer: gzip JSONL partitioned by source and UTC hour.

Layout::

    data/raw/<source>/<YYYY-MM-DD>/<HH>[-<suffix>].json.gz

It is the same format GH Archive ships, so archive hours drop in unchanged and
everything is readable in one stream (or by DuckDB:
``read_json('data/raw/**/*.json.gz')``). Records are never rewritten;
analysis results are always rebuilt from here.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class RawBuffer:
    root: Path

    def partition(self, source: str, hour: datetime, suffix: str = "") -> Path:
        hour = hour.astimezone(timezone.utc)
        name = f"{hour:%H}{'-' + suffix if suffix else ''}.json.gz"
        return self.root / source / f"{hour:%Y-%m-%d}" / name

    def append(
        self,
        source: str,
        records: Iterable[dict[str, Any]],
        hour: datetime | None = None,
        suffix: str = "",
    ) -> int:
        """Append records to the partition of ``hour`` (default: now). Returns count."""
        path = self.partition(source, hour or datetime.now(timezone.utc), suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        # Each append adds a gzip member; concatenated members are valid gzip.
        with gzip.open(path, "at", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(record, separators=(",", ":")) + "\n")
                count += 1
        return count

    def files(self, source: str | None = None) -> list[Path]:
        base = self.root / source if source else self.root
        return sorted(p for p in base.rglob("*.json.gz") if p.is_file())

    def read(self, source: str | None = None) -> Iterator[dict[str, Any]]:
        """Stream every record, file by file, line by line."""
        for path in self.files(source):
            yield from read_jsonl_gz(path)

    def sources(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir() if p.is_dir()) if self.root.exists() else []


def read_jsonl_gz(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)
