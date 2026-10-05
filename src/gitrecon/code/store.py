"""Keeping analysis results: the raw buffer (always) and the map dataset (when the origin is known).

- raw buffer: ``data/raw/analysis/<date>/<HH>.json.gz`` - one record per analysed repository,
  everything ``analyze_repo`` found, with ``analysed_at``; append-only like every other source.
- map: ``<map>/data-heuristicality/code-analysis/<platform>/<owner>/<repository>.json`` - the
  same without what is local (the path on this machine) or changes on every run (the time),
  so the file changes only when the repository does. Only for repositories whose ``origin``
  names a platform, an owner and a name. Private repositories (and those that cannot be shown
  public) stay out unless the caller asks otherwise (``--map-priv-repos``).
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gitrecon.storage.rawbuffer import RawBuffer

SOURCE = "analysis"
MAP_AREA = Path("data-heuristicality", "code-analysis")
REMOTE = re.compile(r"^(?:https?://|ssh://git@|git@)(?P<platform>[\w.-]+\.[a-z]+)[:/](?P<owner>[\w.-]+)/(?P<name>[\w.-]+?)(?:\.git)?/?$")


def _git(path: str, *args: str) -> str:
    done = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True, check=False)
    return done.stdout.strip() if done.returncode == 0 else ""


def origin(path: str | Path) -> dict[str, str] | None:
    """``{"platform", "owner", "name"}`` from the clone's ``origin`` remote; ``None`` when it has none."""
    match = REMOTE.match(_git(str(path), "remote", "get-url", "origin"))
    return match.groupdict() if match else None


def describe(result: dict[str, Any]) -> dict[str, Any]:
    """Add where the repository comes from and which commit was read (``origin``, ``commit``)."""
    result["origin"] = origin(result["path"])
    result["commit"] = _git(result["path"], "rev-parse", "HEAD") or None
    return result


def not_public(results: list[dict[str, Any]], client: Any) -> set[str]:
    """Lowercase ``owner/name`` of analysed repositories that are private - or cannot be shown public.

    One request per repository on github.com (``GET /repos/{owner}/{name}`` -> ``private``).
    Anything else counts as not public: another platform, no answer, no network.
    """
    hidden: set[str] = set()
    for result in results:
        source = result.get("origin")
        if not source:
            continue
        full_name = f"{source['owner']}/{source['name']}"
        public = False
        if source["platform"].lower() == "github.com":
            try:
                public = (client.get(f"/repos/{full_name}").data or {}).get("private") is False
            except Exception:  # noqa: BLE001 - unknown is treated as private
                public = False
        if not public:
            hidden.add(full_name.lower())
    return hidden


def map_path(map_root: Path, source: dict[str, str]) -> Path:
    return map_root / MAP_AREA / source["platform"].lower() / source["owner"].lower() / f"{source['name'].lower()}.json"


def save_analysis(results: list[dict[str, Any]], raw_dir: Path, map_root: Path | None = None,
                  private: set[str] | None = None) -> dict[str, Any]:
    """Append ``results`` to the raw buffer and write them into the map.

    ``private``: lowercase ``owner/name`` of repositories that must stay out of the map (it is
    published). Returns ``{"buffered": n, "mapped": [paths changed], "unmapped": [names]}``.
    """
    now = datetime.now(timezone.utc)
    stamp = now.isoformat(timespec="seconds")
    for result in results:
        if "origin" not in result:
            describe(result)
    buffered = RawBuffer(raw_dir).append(SOURCE, ({**r, "analysed_at": stamp} for r in results), hour=now)
    mapped: list[str] = []
    unmapped: list[str] = []
    for result in results:
        source = result["origin"]
        hidden = source and f"{source['owner']}/{source['name']}".lower() in (private or set())
        if map_root is None or not map_root.is_dir() or not source or hidden:
            unmapped.append(result["name"])
            continue
        record = {k: v for k, v in result.items() if k != "path"}
        text = json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        path = map_path(map_root, source)
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            mapped.append(str(path))
    return {"buffered": buffered, "mapped": mapped, "unmapped": unmapped}
