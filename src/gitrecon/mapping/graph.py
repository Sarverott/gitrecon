"""Activity map: entities as nodes, observed relations as edges."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from gitrecon.models import Entity, Event, Gist, User, from_record


@dataclass(frozen=True)
class Edge:
    source: str  # entity key
    relation: str
    target: str  # entity key


@dataclass
class ActivityGraph:
    nodes: dict[str, Entity] = field(default_factory=dict)
    # edge -> ids of the events/gists that evidence it
    edges: dict[Edge, list[str]] = field(default_factory=lambda: defaultdict(list))

    def add_node(self, entity: Entity) -> str:
        # Keep the richest version seen: full API payloads beat short event stubs.
        current = self.nodes.get(entity.key)
        if current is None or len(entity.raw) > len(current.raw):
            self.nodes[entity.key] = entity
        return entity.key

    def link(self, source: Entity, relation: str, target: Entity, evidence: str) -> None:
        edge = Edge(self.add_node(source), relation, self.add_node(target))
        self.edges[edge].append(evidence)

    def add_event(self, event: Event) -> None:
        actor, repo, org = event.actor, event.repo, event.org
        if actor and repo:
            self.link(actor, event.type, repo, event.id)
        if repo and org:
            self.link(repo, "belongs_to", org, event.id)
        elif repo and repo.owner:
            # No org on the event: the owner is a user (stub merges with richer nodes by key).
            self.link(repo, "owned_by", User(login=repo.owner), event.id)
        if actor and org:
            self.link(actor, "active_in", org, event.id)
        if repo and (forkee := event.forkee):
            self.link(repo, "forked_to", forkee, event.id)
        if event.type == "MemberEvent" and repo and (member := event.payload.get("member")):
            self.link(User.from_api(member), "member_of", repo, event.id)

    def add_gist(self, gist: Gist) -> None:
        self.add_node(gist)
        if gist.owner:
            self.link(User(login=gist.owner), "created_gist", gist, gist.id)

    def ingest(self, records: Iterable[dict[str, Any]]) -> None:
        """Feed raw buffer records; events and gists are told apart by shape."""
        for record in records:
            item = from_record(record)
            if isinstance(item, Event):
                self.add_event(item)
            elif isinstance(item, Gist):
                self.add_gist(item)

    def neighbors(self, key: str) -> list[tuple[str, str]]:
        """(relation, other key) pairs touching ``key``, both directions."""
        out = [(e.relation, e.target) for e in self.edges if e.source == key]
        out += [(f"~{e.relation}", e.source) for e in self.edges if e.target == key]
        return out

    def summary(self) -> dict[str, Any]:
        kinds = Counter(node.kind for node in self.nodes.values())
        relations = Counter()
        for edge, evidence in self.edges.items():
            relations[edge.relation] += len(evidence)
        degree = Counter()
        for edge, evidence in self.edges.items():
            degree[edge.source] += len(evidence)
            degree[edge.target] += len(evidence)
        return {
            "nodes": dict(kinds),
            "edges": len(self.edges),
            "relations": dict(relations.most_common()),
            "hubs": degree.most_common(10),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() | {"key": key} for key, node in self.nodes.items()],
            "edges": [
                {"source": e.source, "relation": e.relation, "target": e.target, "evidence": ev}
                for e, ev in self.edges.items()
            ],
        }

