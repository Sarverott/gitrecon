"""CaptorLex, step 2, second circle: how the repositories of one owner hold on to each other.

    relations = owner_relations("~/__WORKSHOP/forge/rattish")

Two kinds of tie, strongest first:

1. **submodule** - one repository carries another inside itself (``.gitmodules``): it cannot be
   built or even fully checked out without it;
2. **dependency** - a manifest names another repository's package (by the name that
   repository publishes: ``package.json`` name, ``[project] name``, composer name, crate name,
   Go module path) or points straight at its git URL. Softer: versions, registries and
   replacements stand in between.

Links in code and text are a weaker tie still and belong to a later circle.
"""

from __future__ import annotations

import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

from gitrecon.code import frameworks
from gitrecon.code.analyze import find_repos, repo_files
from gitrecon.code.store import REMOTE, origin

SUBMODULE, DEPENDENCY = "submodule", "dependency"
GIT_URL = re.compile(r"(?:github\.com[:/]|github:|gitlab\.com[:/]|gitlab:)([\w.-]+)/([\w.-]+?)(?:\.git)?(?:[#@/?].*)?$")


def _toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def published_names(root: Path) -> dict[str, str]:
    """Ecosystem -> the package name this repository publishes (from its root manifests)."""
    names: dict[str, str] = {}
    if name := _json(root / "package.json").get("name"):
        names["npm"] = str(name)
    if name := _json(root / "composer.json").get("name"):
        names["composer"] = str(name)
    pyproject = _toml(root / "pyproject.toml")
    name = (pyproject.get("project") or {}).get("name") or ((pyproject.get("tool") or {}).get("poetry") or {}).get("name")
    if name:
        names["pypi"] = str(name).lower().replace("_", "-")
    if name := (_toml(root / "Cargo.toml").get("package") or {}).get("name"):
        names["cargo"] = str(name)
    try:
        module = re.search(r"^module\s+(\S+)", (root / "go.mod").read_text(encoding="utf-8"), re.MULTILINE)
    except OSError:
        module = None
    if module:
        names["go"] = module.group(1)
    return names


def submodules(root: Path) -> list[dict[str, str]]:
    """``{"path", "url"}`` of every submodule ``.gitmodules`` declares."""
    if not (root / ".gitmodules").is_file():
        return []
    # --null: "key\nvalue\0" - a submodule's name may hold spaces
    done = subprocess.run(["git", "config", "--null", "-f", str(root / ".gitmodules"), "--get-regexp",
                           r"^submodule\..*\.(url|path)$"], capture_output=True, text=True, check=False)
    found: dict[str, dict[str, str]] = {}
    for entry in done.stdout.split("\0"):
        key, _, value = entry.partition("\n")
        if not key.startswith("submodule.") or "." not in key[len("submodule."):]:
            continue
        name, field = key[len("submodule."):].rsplit(".", 1)
        found.setdefault(name, {})[field] = value
    return [{"path": entry.get("path", name), "url": entry["url"]} for name, entry in sorted(found.items()) if "url" in entry]


def _git_dependencies(root: Path) -> list[tuple[str, str, str]]:
    """``(owner, name, where)`` for dependencies given as git URLs rather than package names."""
    found = []
    for manifest, keys in (("package.json", ("dependencies", "devDependencies", "peerDependencies")),
                           ("composer.json", ("require", "require-dev"))):
        data = _json(root / manifest)
        for key in keys:
            for value in (data.get(key) or {}).values():
                if isinstance(value, str) and (match := GIT_URL.search(value)):
                    found.append((match.group(1), match.group(2), manifest))
        for repository in data.get("repositories") or [] if manifest == "composer.json" else []:
            if isinstance(repository, dict) and (match := GIT_URL.search(str(repository.get("url", "")))):
                found.append((match.group(1), match.group(2), manifest))
    for requirements in root.glob("requirements*.txt"):
        for line in requirements.read_text(encoding="utf-8", errors="replace").splitlines():
            if "git+" in line and (match := GIT_URL.search(line.split("#")[0].strip())):
                found.append((match.group(1), match.group(2), requirements.name))
    return found


def owner_relations(folder: str | Path) -> dict[str, Any]:
    """Repositories directly inside ``folder`` and the ties between them (and outward submodules)."""
    root = Path(folder).expanduser().resolve()
    repos = find_repos(root)
    entries: dict[str, dict[str, Any]] = {}
    by_origin: dict[str, str] = {}
    by_package: dict[tuple[str, str], str] = {}
    for repo in repos:
        source = origin(repo)
        names = published_names(repo)
        entries[repo.name] = {"name": repo.name, "origin": source, "publishes": names, "path": str(repo)}
        if source:
            by_origin[f"{source['owner']}/{source['name']}".lower()] = repo.name
        for ecosystem, name in names.items():
            by_package.setdefault((ecosystem, name), repo.name)

    edges: list[dict[str, str]] = []
    outside: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def tie(source: str, target: str, kind: str, detail: str) -> None:
        if source != target and (source, target, kind) not in seen:
            seen.add((source, target, kind))
            edges.append({"from": source, "to": target, "kind": kind, "detail": detail})

    for repo in repos:
        own = entries[repo.name]["origin"]
        for module in submodules(repo):
            url = module["url"]
            if url.startswith(("../", "./")) and own:  # relative to this repository's own URL
                key = f"{own['owner']}/{url.rstrip('/').rsplit('/', 1)[-1].removesuffix('.git')}".lower()
            else:
                match = REMOTE.match(url)
                key = f"{match['owner']}/{match['name']}".lower() if match else ""
            if key in by_origin:
                tie(repo.name, by_origin[key], SUBMODULE, module["path"])
            else:
                outside.append({"from": repo.name, "url": url, "path": module["path"]})
        for ecosystem, names in frameworks.dependencies(repo, repo_files(repo)).items():
            for name in names:
                target = by_package.get((ecosystem, name))
                if target is None and ecosystem == "go":
                    target = next((r for (eco, module), r in by_package.items() if eco == "go" and name.startswith(module)), None)
                if target:
                    tie(repo.name, target, DEPENDENCY, f"{ecosystem}: {name}")
        for owner, name, where in _git_dependencies(repo):
            if (target := by_origin.get(f"{owner}/{name}".lower())):
                tie(repo.name, target, DEPENDENCY, f"git URL in {where}")

    edges.sort(key=lambda e: (e["kind"] != SUBMODULE, e["from"], e["to"]))  # the stronger tie first
    tied = {name for edge in edges for name in (edge["from"], edge["to"])}
    return {"folder": str(root), "name": root.name, "repositories": [entries[r.name] for r in repos], "edges": edges,
            "outside_submodules": outside, "untied": sorted(set(entries) - tied)}


def relations_mermaid(relations: dict[str, Any], show_untied: bool = False) -> str:
    """Mermaid flowchart: thick arrows for submodules, dashed for dependencies."""
    ident = lambda name: "r_" + re.sub(r"[^0-9A-Za-z]", "_", name)  # noqa: E731
    shown = {name for edge in relations["edges"] for name in (edge["from"], edge["to"])}
    shown |= {module["from"] for module in relations["outside_submodules"]}
    if show_untied:
        shown |= set(relations["untied"])
    lines = ["flowchart LR"]
    lines += [f'  {ident(name)}["{name}"]' for name in sorted(shown)]
    for edge in relations["edges"]:
        label = edge["detail"].replace('"', "'")
        arrow = "==>" if edge["kind"] == SUBMODULE else "-.->"
        lines.append(f'  {ident(edge["from"])} {arrow}|"{edge["kind"]}: {label}"| {ident(edge["to"])}')
    for index, module in enumerate(relations["outside_submodules"]):
        match = REMOTE.match(module["url"])
        name = (f"{match['owner']}/{match['name']}" if match else module["url"]).replace('"', "'")
        lines.append(f'  out_{index}("{name}"):::outside')
        lines.append(f'  {ident(module["from"])} ==>|"submodule: {module["path"]}"| out_{index}')
    lines.append("  classDef outside fill:#f8fafc,stroke:#64748b,stroke-dasharray:4 3,color:#0f172a")
    return "\n".join(lines) + "\n"
