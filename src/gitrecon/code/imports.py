"""CaptorLex, step 2 (inside one repository): which file uses which.

    graph = import_graph("~/__WORKSHOP/forge/redscope-technologies/gitrecon")

Python is read exactly, through ``ast``, with module names resolved to the repository's
files. Other languages are read by the patterns in ``resources/imports.yml`` (import /
require / include statements) and their rules for turning a target into a file. What does
not resolve to a file of the repository is *external*: a library, or a file that is not there.
"""

from __future__ import annotations

import ast
import json
import posixpath
import re
from collections import Counter
from functools import cache
from pathlib import Path
from typing import Any

import networkx as nx
import yaml

from gitrecon.code.analyze import MAX_FILE_BYTES, _read, repo_files
from gitrecon.code.languages import detect
from gitrecon.config import resource

TOP = 15


@cache
def rules() -> dict[str, Any]:
    table = yaml.safe_load(resource("imports.yml").read_text(encoding="utf-8"))["languages"]
    for spec in table.values():
        for key in ("patterns", "external"):
            if spec.get(key) and isinstance(spec[key][0], str):
                spec[key] = [re.compile(pattern, re.MULTILINE) for pattern in spec[key]]
    return table


# --- Python: module names -> files ---------------------------------------------------------


def _python_modules(files: set[str]) -> dict[str, str]:
    """Dotted module name -> file, for every Python file, from its source root and from the repository root."""
    folders_with_init = {posixpath.dirname(f) for f in files if posixpath.basename(f) == "__init__.py"}
    modules: dict[str, str] = {}
    for file in sorted(files):
        if not file.endswith((".py", ".pyi")):
            continue
        parts = file.rsplit(".", 1)[0].split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        root = len(parts) - 1  # the nearest ancestor that is not a package is the source root
        while root > 0 and "/".join(file.split("/")[:root]) in folders_with_init:
            root -= 1
        for start in {0, root}:
            if parts[start:]:
                modules.setdefault(".".join(parts[start:]), file)
    return modules


def _python_targets(source: str, file: str, modules: dict[str, str], is_package: bool) -> tuple[set[str], set[str]]:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return set(), set()
    own = next((name for name, path in modules.items() if path == file), "")
    package = own.split(".") if is_package else own.split(".")[:-1]
    internal: set[str] = set()
    external: set[str] = set()

    def use(name: str) -> bool:
        # the longest prefix that is a module of the repository
        parts = name.split(".")
        for end in range(len(parts), 0, -1):
            if (target := modules.get(".".join(parts[:end]))):
                internal.add(target)
                return True
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not use(alias.name):
                    external.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - (node.level - 1)] if node.level - 1 <= len(package) else []
                prefix = ".".join([*base, *(node.module.split(".") if node.module else [])])
            else:
                prefix = node.module or ""
            found = [use(f"{prefix}.{alias.name}" if prefix else alias.name) for alias in node.names]
            if not any(found) and not use(prefix) and not node.level and prefix:
                external.add(prefix.split(".")[0])
    internal.discard(file)
    return internal, external


# --- other languages: patterns -> files ------------------------------------------------------


def _resolve(target: str, file: str, spec: dict[str, Any], files: set[str], by_suffix: dict[str, list[str]]) -> str | None:
    how = spec.get("resolve", "relative")
    target = target.split("?")[0].split("#")[0]
    if how == "relative" and not target.startswith("."):
        return None
    folder = posixpath.dirname(file)
    bases = [posixpath.normpath(posixpath.join(folder, target))]
    if how in ("path", "include"):
        bases.append(posixpath.normpath(target.lstrip("/")))
    for base in bases:
        if base.startswith(".."):
            continue
        candidates = [base, *(base + ext for ext in spec.get("extensions", [])),
                      *(posixpath.join(base, index) for index in spec.get("index", []))]
        if base.endswith(".js"):  # TypeScript sources are imported under the name of their output
            candidates += [base[:-3] + ".ts", base[:-3] + ".tsx"]
        for candidate in candidates:
            if candidate in files:
                return candidate
    if how == "include":
        matches = by_suffix.get(posixpath.basename(target), [])
        matches = [m for m in matches if m == target or m.endswith("/" + target.lstrip("./"))]
        if len(matches) == 1:
            return matches[0]
    return None


def _psr4(root: Path) -> dict[str, str]:
    """``{"App\\\\": "app/"}`` from composer.json (autoload and autoload-dev)."""
    try:
        composer = json.loads((root / "composer.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    table: dict[str, str] = {}
    for section in ("autoload", "autoload-dev"):
        for prefix, folder in ((composer.get(section) or {}).get("psr-4") or {}).items():
            table[prefix] = (folder[0] if isinstance(folder, list) else folder).strip("/")
    return table


# unindented only: an indented `use X;` inside a class is a trait, not an import
PHP_USE = re.compile(r"^use[ \t]+(?:function[ \t]+|const[ \t]+)?\\?([A-Za-z_][\w\\]*)", re.MULTILINE)


def _php_uses(text: str, psr4: dict[str, str], files: set[str]) -> tuple[set[str], set[str]]:
    internal: set[str] = set()
    external: set[str] = set()
    for name in PHP_USE.findall(text):
        for prefix, folder in sorted(psr4.items(), key=lambda kv: -len(kv[0])):
            if name.startswith(prefix):
                path = posixpath.join(folder, name[len(prefix):].replace("\\", "/") + ".php").lstrip("/")
                if path in files:
                    internal.add(path)
                break
        else:
            external.add(name.split("\\")[0])
    return internal, external


# --- the graph --------------------------------------------------------------------------------


def import_graph(path: str | Path) -> dict[str, Any]:
    """``{"files": [...], "edges": [[from, to]], "external": {name: files using it}, ...}`` with a summary."""
    root = Path(path).expanduser().resolve()
    listed = {p.relative_to(root).as_posix(): p for p in repo_files(root)}
    files = set(listed)
    by_suffix: dict[str, list[str]] = {}
    for file in files:
        by_suffix.setdefault(posixpath.basename(file), []).append(file)
    modules = _python_modules(files)
    packages = {posixpath.dirname(f) for f in files if posixpath.basename(f) == "__init__.py"}
    psr4 = _psr4(root)
    table = rules()

    graph = nx.DiGraph()
    external: Counter[str] = Counter()
    read: Counter[str] = Counter()
    for file, real in sorted(listed.items()):
        language = detect(real)
        if language is None or not (language.name == "Python" or language.name in table):
            continue
        try:
            if real.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        text = _read(real)
        if text is None:
            continue
        read[language.name] += 1
        graph.add_node(file, language=language.name)
        if language.name == "Python":
            inside, outside = _python_targets(text, file, modules, posixpath.basename(file) == "__init__.py"
                                              and posixpath.dirname(file) in packages)
        else:
            spec = table[language.name]
            inside, outside = set(), set()
            for pattern in spec["patterns"]:
                for target in pattern.findall(text):
                    if (found := _resolve(target, file, spec, files, by_suffix)) and found != file:
                        inside.add(found)
                    elif not target.startswith("."):
                        outside.add(target.split("/")[0] if not target.startswith("@") else "/".join(target.split("/")[:2]))
            for pattern in spec.get("external", []):
                outside.update(pattern.findall(text))
            if spec.get("psr4") and psr4:
                more_inside, more_outside = _php_uses(text, psr4, files)
                inside |= more_inside - {file}
                outside |= more_outside
        for target in inside:
            graph.add_edge(file, target)
        external.update(outside)

    cycles = sorted((sorted(group) for group in nx.strongly_connected_components(graph) if len(group) > 1),
                    key=lambda group: (-len(group), group))
    used = sorted(graph.in_degree, key=lambda kv: (-kv[1], kv[0]))
    using = sorted(graph.out_degree, key=lambda kv: (-kv[1], kv[0]))
    return {
        "path": str(root),
        "name": root.name,
        "languages": dict(read.most_common()),
        "files": sorted(graph.nodes),
        "edges": sorted([source, target] for source, target in graph.edges),
        "most_used": [{"file": f, "used_by": n} for f, n in used[:TOP] if n],
        "uses_most": [{"file": f, "uses": n} for f, n in using[:TOP] if n],
        "unconnected": sorted(f for f in graph.nodes if graph.degree(f) == 0),
        "cycles": cycles,
        "external": dict(external.most_common()),
    }


def folder_edges(graph: dict[str, Any], depth: int = 3) -> Counter[tuple[str, str]]:
    """The graph collapsed to folders ``depth`` levels deep: ``(from, to) -> imports``."""
    def folder(file: str) -> str:
        parts = file.split("/")[:-1]
        return "/".join(parts[:depth]) or "."
    edges: Counter[tuple[str, str]] = Counter()
    for source, target in graph["edges"]:
        if folder(source) != folder(target):
            edges[(folder(source), folder(target))] += 1
    return edges


def imports_mermaid(graph: dict[str, Any], level: str = "folder", depth: int = 3, max_nodes: int = 80) -> str:
    """Mermaid flowchart: folders with weighted arrows, or files grouped by folder."""
    ident = lambda name: "n_" + re.sub(r"[^0-9A-Za-z]", "_", name)  # noqa: E731
    lines = ["flowchart LR"]
    if level == "folder":
        edges = folder_edges(graph, depth)
        for name in sorted({n for pair in edges for n in pair}):
            lines.append(f'  {ident(name)}["{name}"]')
        for (source, target), count in sorted(edges.items(), key=lambda kv: (-kv[1], kv[0])):
            arrow = "==>" if count >= 5 else "-->"
            lines.append(f'  {ident(source)} {arrow}|"{count}"| {ident(target)}')
        return "\n".join(lines) + "\n"
    degree: Counter[str] = Counter()
    for source, target in graph["edges"]:
        degree[source] += 1
        degree[target] += 1
    keep = {name for name, _ in sorted(degree.items(), key=lambda kv: (-kv[1], kv[0]))[:max_nodes]}
    in_cycle = {name for group in graph["cycles"] for name in group}
    for folder in sorted({posixpath.dirname(f) or "." for f in keep}):
        lines.append(f'  subgraph {ident("dir/" + folder)}["{folder}"]')
        for file in sorted(f for f in keep if (posixpath.dirname(f) or ".") == folder):
            lines.append(f'    {ident(file)}["{posixpath.basename(file)}"]' + (":::cycle" if file in in_cycle else ""))
        lines.append("  end")
    for source, target in graph["edges"]:
        if source in keep and target in keep:
            lines.append(f"  {ident(source)} --> {ident(target)}")
    if len(degree) > len(keep):
        lines.append(f"  %% {len(degree) - len(keep)} more files not drawn (max_nodes={max_nodes})")
    lines.append("  classDef cycle fill:#fee2e2,stroke:#dc2626,color:#7f1d1d")
    return "\n".join(lines) + "\n"
