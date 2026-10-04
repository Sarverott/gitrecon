"""Drawing networks: Mermaid (GitHub, Obsidian and the docs site render it), DOT, JSON.

Two zoom levels of the same ``ActivityGraph``:

- ``owners``: one node per user / organization; edges are memberships and "forks from"
  with a count - the readable overview, whatever the number of repositories
- ``repos``: one node per repository, grouped by owner; edges are ``fork_of``. Mermaid slows
  down past a few hundred nodes, so the most connected repositories are kept (``max_nodes``).
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from gitrecon.mapping.graph import ActivityGraph
from gitrecon.mapping.network import FORK_OF, OWNED_BY, owner_network
from gitrecon.models.base import url_for_key

CLASSES = """classDef user fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
classDef org fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
classDef outside fill:#f8fafc,stroke:#64748b,stroke-width:1px,color:#0f172a,stroke-dasharray:4 3
classDef repo fill:#ecfdf5,stroke:#059669,stroke-width:1px,color:#064e3b
classDef fork fill:#f8fafc,stroke:#94a3b8,stroke-width:1px,color:#334155"""


def node_id(key: str) -> str:
    """A Mermaid-safe id for an entity key (``repo:a/b.c`` -> ``repo_a_b_c``)."""
    return re.sub(r"[^0-9A-Za-z_]", "_", key)


def _label(text: str) -> str:
    return text.replace('"', "'")


def _name(key: str, graph: ActivityGraph | None = None) -> str:
    """The entity's name as GitHub spells it (keys are lowercase)."""
    node = graph.nodes.get(key) if graph else None
    return getattr(node, "login", None) or getattr(node, "full_name", None) or key.split(":", 1)[1]


def owners_mermaid(graph: ActivityGraph, min_forks: int = 1) -> str:
    """Owner-level overview: memberships, and who forks from whom at least ``min_forks`` times."""
    net = owner_network(graph)
    owners = net["owners"]
    # the user, their organizations (even empty ones) and every owner with listed repositories
    listed = {key for key, stats in owners.items() if stats["repos"]} | {k for pair in net["members"] for k in pair}
    forks = {pair: n for pair, n in net["forks"].items() if n >= min_forks and pair[0] != pair[1]}
    shown = listed | {key for pair in forks for key in pair}
    lines = ["flowchart LR"]
    for key in sorted(shown, key=lambda k: (k not in listed, k)):
        stats, name = owners[key], _label(_name(key, graph))
        if key in listed:
            text = f"{name}<br/>{stats['repos']} repos · {stats['forks']} forks · ★{stats['stars']}"
            shape = f'(["{text}"])' if stats["kind"] == "user" else f'["{text}"]'
            css = stats["kind"]
        else:
            shape, css = f'("{name}")', "outside"
        lines.append(f"  {node_id(key)}{shape}:::{css}")
    for user, org in sorted(net["members"]):
        lines.append(f"  {node_id(user)} -->|member| {node_id(org)}")
    for (source, target), n in sorted(forks.items(), key=lambda item: -item[1]):
        arrow = "==>" if n >= 5 else "-.->"
        lines.append(f'  {node_id(source)} {arrow}|"{n} fork{"s" if n > 1 else ""}"| {node_id(target)}')
    for key in sorted(shown):
        if url := url_for_key(key):
            lines.append(f'  click {node_id(key)} "{url}"')
    return "\n".join([*lines, CLASSES])


def repos_mermaid(graph: ActivityGraph, max_nodes: int = 150, forks_only: bool = False) -> str:
    """Repository-level: repositories grouped by owner, ``fork_of`` edges between them."""
    owned = {e.source: e.target for e in graph.edges if e.relation == OWNED_BY}
    fork_edges = [(e.source, e.target) for e in graph.edges if e.relation == FORK_OF]
    degree: Counter[str] = Counter()
    for source, target in fork_edges:
        degree[source] += 1
        degree[target] += 1
    candidates = [k for k in owned if degree[k] or not forks_only]
    # most connected first, then most starred
    candidates.sort(key=lambda k: (-degree[k], -(graph.nodes[k].stargazers_count or 0), k))
    keep = set(candidates[:max_nodes])
    lines = ["flowchart LR"]
    for owner_key in sorted({owned[k] for k in keep}):
        lines.append(f'  subgraph {node_id(owner_key)}["{_label(_name(owner_key, graph))}"]')
        for key in sorted(k for k in keep if owned[k] == owner_key):
            node = graph.nodes[key]
            name = _label(node.name)
            stars = f" ★{node.stargazers_count}" if node.stargazers_count else ""
            css = "outside" if not node.raw else "fork" if node.fork else "repo"  # no listing: an upstream
            lines.append(f'    {node_id(key)}["{name}{stars}"]:::{css}')
        lines.append("  end")
    for source, target in sorted(fork_edges):
        if source in keep and target in keep:
            lines.append(f"  {node_id(source)} -->|fork of| {node_id(target)}")
    dropped = len(candidates) - len(keep)
    if dropped:
        lines.append(f"  %% {dropped} more repositories not drawn (max_nodes={max_nodes})")
    return "\n".join([*lines, CLASSES])


def to_dot(graph: ActivityGraph) -> str:
    """Graphviz DOT of the whole graph (for Gephi, ``dot -Tsvg`` ...)."""
    lines = ["digraph gitrecon {", "  rankdir=LR;", '  node [shape=box, fontname="sans-serif"];']
    for key, node in sorted(graph.nodes.items()):
        shape = {"user": "ellipse", "org": "box3d"}.get(node.kind, "box")
        lines.append(f'  "{key}" [label="{_label(_name(key, graph))}", shape={shape}];')
    for edge in sorted(graph.edges, key=lambda e: (e.source, e.relation, e.target)):
        lines.append(f'  "{edge.source}" -> "{edge.target}" [label="{edge.relation}"];')
    return "\n".join([*lines, "}"])


def to_json(graph: ActivityGraph) -> dict[str, Any]:
    """Nodes and edges for programs (a web frontend, d3, cytoscape...), plus the owner overview."""
    net = owner_network(graph)
    return {
        "nodes": [{"key": key, "kind": node.kind, "name": _name(key, graph), "url": node.html_url,
                   "fork": getattr(node, "fork", None), "stars": getattr(node, "stargazers_count", None),
                   "language": getattr(node, "language", None)}
                  for key, node in sorted(graph.nodes.items())],
        "edges": [{"source": e.source, "relation": e.relation, "target": e.target}
                  for e in sorted(graph.edges, key=lambda e: (e.source, e.relation, e.target))],
        "owners": {key: stats for key, stats in sorted(net["owners"].items())},
        "owner_forks": [{"source": s, "target": t, "count": n} for (s, t), n in sorted(net["forks"].items())],
    }
