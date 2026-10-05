"""Frameworks and tools of a repository, from its manifests and marker files.

What counts is declared in ``resources/frameworks.yml``: which dependency files exist and how
to read them, which package means which framework, and which files give a tool away.
"""

from __future__ import annotations

import fnmatch
import json
import re
import tomllib
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from gitrecon.config import resource

REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


@cache
def rules() -> dict[str, Any]:
    return yaml.safe_load(resource("frameworks.yml").read_text(encoding="utf-8"))


def _normal(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def _requirement(spec: str) -> str | None:
    match = REQUIREMENT_NAME.match(spec)
    return _normal(match.group(1)) if match else None


# --- readers: one manifest file -> package names ---------------------------------------


def read_json_keys(path: Path, keys: list[str]) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [name for key in keys for name in (data.get(key) or {}) if name != "php" and not name.startswith("ext-")]


def read_toml_keys(path: Path, keys: list[str]) -> list[str]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return [_normal(name) for key in keys for name in (data.get(key) or {})]


def read_pyproject(path: Path, keys: list[str] | None = None) -> list[str]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project") or {}
    specs: list[Any] = list(project.get("dependencies") or [])
    for group in (project.get("optional-dependencies") or {}).values():
        specs += group
    for group in (data.get("dependency-groups") or {}).values():
        specs += [s for s in group if isinstance(s, str)]
    names = [n for n in map(_requirement, specs) if n]
    poetry = ((data.get("tool") or {}).get("poetry") or {}).get("dependencies") or {}
    return names + [_normal(n) for n in poetry if n.lower() != "python"]


def read_requirements(path: Path, keys: list[str] | None = None) -> list[str]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [n for line in lines if line.strip() and not line.strip().startswith(("#", "-")) and "://" not in line
            if (n := _requirement(line))]  # a line that is an address names no package (relations reads those)


def read_gomod(path: Path, keys: list[str] | None = None) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return re.findall(r"^\s*(?:require\s+)?([a-z0-9.\-]+\.[a-z]+/[^\s]+)\s+v[0-9]", text, re.MULTILINE)


def read_gemfile(path: Path, keys: list[str] | None = None) -> list[str]:
    return re.findall(r"""^\s*gem\s+['"]([^'"]+)['"]""", path.read_text(encoding="utf-8", errors="replace"),
                      re.MULTILINE)


READERS = {"json_keys": read_json_keys, "toml_keys": read_toml_keys, "pyproject": read_pyproject,
           "requirements": read_requirements, "gomod": read_gomod, "gemfile": read_gemfile}


def dependencies(root: Path, files: list[Path]) -> dict[str, list[str]]:
    """Ecosystem -> package names declared in the repository's manifests (anywhere in it)."""
    found: dict[str, set[str]] = {}
    for pattern, spec in rules()["manifests"].items():
        for path in files:
            if not fnmatch.fnmatch(path.name, pattern):
                continue
            try:
                names = READERS[spec["reader"]](path, spec.get("keys") or [])
            except Exception:  # noqa: BLE001 - a broken manifest is not our problem
                continue
            found.setdefault(spec["ecosystem"], set()).update(names)
    return {ecosystem: sorted(names) for ecosystem, names in sorted(found.items())}


def detect(root: Path, files: list[Path]) -> tuple[list[str], dict[str, list[str]]]:
    """``(frameworks and tools, dependencies by ecosystem)`` of the repository at ``root``."""
    deps = dependencies(root, files)
    table = rules()
    found: set[str] = set()
    for ecosystem, names in deps.items():
        known = {_normal(k) if ecosystem == "pypi" else k: v for k, v in (table["packages"].get(ecosystem) or {}).items()}
        for name in names:
            if name in known:
                found.add(known[name])
            elif ecosystem == "go":  # module paths carry versions and subpackages
                found.update(v for k, v in known.items() if name.startswith(k))
    relative = {p.relative_to(root).as_posix() for p in files}
    folders = {parent.as_posix() for p in relative for parent in Path(p).parents if parent.as_posix() != "."}
    for pattern, tool in table["files"].items():
        if any(fnmatch.fnmatch(name, pattern) for name in relative | folders):
            found.add(tool)
    return sorted(found, key=str.lower), deps
