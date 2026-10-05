"""What differs from the last commit: the files, their diffs, what is known about them, their order.

Nothing here decides anything about messages - it is the ground every commit handler
stands on (``gitrecon.committing.handlers``).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_DIFF_CHARS = 3000


def _git(repo: Path, *args: str, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False, errors="replace",
                          env=env)
    if check and done.returncode != 0:
        raise RuntimeError(done.stderr.strip() or done.stdout.strip() or f"git {' '.join(args)} failed")
    return done


@dataclass
class Change:
    path: str
    status: str  # added | modified | deleted | renamed
    old_path: str | None = None


def changed_files(repo: str | Path) -> list[Change]:
    """Every file that differs from the last commit: modified, new (untracked too), deleted, renamed."""
    root = Path(repo).expanduser()
    entries = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout.split("\0")
    changes, index = [], 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        if "R" in code or "C" in code:
            old = entries[index]
            index += 1
            if code[1] == "D":  # renamed in the index, then removed: what is left is the old file gone
                changes.append(Change(old, "deleted"))
            else:
                changes.append(Change(path, "renamed", old))
        elif "D" in code:
            changes.append(Change(path, "deleted"))
        elif code == "??" or "A" in code:
            changes.append(Change(path, "added"))
        else:
            changes.append(Change(path, "modified"))
    return changes


def file_diff(repo: str | Path, change: Change, limit: int = MAX_DIFF_CHARS) -> str:
    """What the model is shown for one file: its diff against the last commit, or its beginning when new."""
    root = Path(repo).expanduser()
    if change.status == "added":
        try:
            data = (root / change.path).read_bytes()
        except OSError:
            return "(unreadable)"
        if b"\0" in data[:8000]:
            return f"(a new binary file, {len(data)} bytes)"
        text = "\n".join("+" + line for line in data.decode("utf-8", errors="replace").splitlines())
    else:
        paths = [p for p in (change.old_path, change.path) if p]
        text = _git(root, "diff", "HEAD", "--no-color", "-M", "--", *paths, check=False).stdout
    if limit and len(text) > limit:
        text = text[:limit] + f"\n... ({len(text) - limit} more characters of this diff not shown)"
    return text or "(no textual difference)"


def _rank(path: str) -> int:
    name = path.lower()
    if re.search(r"(^|/)tests?/|(^|/)test_[^/]*$|\.test\.|\.spec\.", name):
        return 2
    if name.endswith((".md", ".rst", ".txt")) or name.startswith("docs/"):
        return 3
    return 0 if re.search(r"\.(py|js|ts|tsx|jsx|php|c|cpp|h|go|rs|rb|sh|lark)$", name) else 1


def order_changes(repo: str | Path, changes: list[Change]) -> list[Change]:
    """Files other changed files import first; then code, configuration, tests, prose - each by path."""
    import networkx as nx

    from gitrecon.code.imports import import_graph

    names = {c.path for c in changes}
    graph = nx.DiGraph()
    graph.add_nodes_from(names)
    try:
        edges = import_graph(repo, untracked=True)["edges"]  # new files are part of what is being committed
    except Exception:  # noqa: BLE001 - ordering is a nicety; without the graph the ranks still apply
        edges = []
    graph.add_edges_from((target, source) for source, target in edges if source in names and target in names)
    depth = {name: 0 for name in names}
    condensed = nx.condensation(graph)  # import cycles become one step
    for node in nx.topological_sort(condensed):
        level = max((condensed.nodes[p]["level"] + 1 for p in condensed.predecessors(node)), default=0)
        condensed.nodes[node]["level"] = level
        for member in condensed.nodes[node]["members"]:
            depth[member] = level
    return sorted(changes, key=lambda c: (_rank(c.path), depth[c.path], c.path))


def file_facts(repo: str | Path, change: Change, graph: dict[str, Any] | None = None) -> dict[str, Any]:
    """Facts gitrecon's own readers have about a changed file: language, size of the change, relations."""
    from gitrecon.code.languages import detect

    root = Path(repo).expanduser()
    language = detect(Path(change.path))
    facts: dict[str, Any] = {"path": change.path, "status": change.status,
                             "language": language.name if language else None,
                             "kind": language.kind if language else None}
    stat = _git(root, "diff", "HEAD", "--numstat", "--", change.path, check=False).stdout.split()
    if len(stat) >= 2 and stat[0].isdigit() and stat[1].isdigit():
        facts["lines_added"], facts["lines_deleted"] = int(stat[0]), int(stat[1])
    elif change.status == "added":
        try:
            facts["lines_added"] = len((root / change.path).read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            pass
    if graph:
        facts["imports"] = sorted(target for source, target in graph["edges"] if source == change.path)[:12]
        users = sorted(source for source, target in graph["edges"] if target == change.path)
        facts["used_by"] = len(users)
        facts["used_by_examples"] = users[:5]
    return facts
