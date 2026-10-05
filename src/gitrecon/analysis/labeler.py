"""Groups activity per entity and runs the rule sets over it."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from gitrecon.analysis import rules
from gitrecon.analysis.rules import Thresholds
from gitrecon.models import Event, Gist, Label, User, from_record


@dataclass
class Labeler:
    thresholds: Thresholds = field(default_factory=Thresholds)
    by_actor: dict[str, list[Event]] = field(default_factory=lambda: defaultdict(list))
    by_repo: dict[str, list[Event]] = field(default_factory=lambda: defaultdict(list))
    by_gist_owner: dict[str, list[Gist]] = field(default_factory=lambda: defaultdict(list))

    def add_event(self, event: Event) -> None:
        if not event.created_at:
            return
        if event.actor:
            self.by_actor[event.actor.key].append(event)
        if event.repo:
            self.by_repo[event.repo.key].append(event)

    def add_gist(self, gist: Gist) -> None:
        if gist.owner and gist.created_at:
            self.by_gist_owner[User(login=gist.owner).key].append(gist)

    def ingest(self, records: Iterable[dict[str, Any]]) -> None:
        for record in records:
            item = from_record(record)
            if isinstance(item, Event):
                self.add_event(item)
            elif isinstance(item, Gist):
                self.add_gist(item)

    def _commit_labels(self) -> list[Label]:
        """What the commit messages of pushes say about a repository (``gitrecon.humanish``).

        Only where the event carries them: GH Archive hours and older Events API answers do,
        current Events API pushes do not.
        """
        from gitrecon.humanish import commit_labels, parse_commit

        labels: list[Label] = []
        for target, events in self.by_repo.items():
            commits = [parse_commit(c.get("message") or "", sha=c.get("sha"))
                       for e in events if e.type == "PushEvent" for c in (e.payload.get("commits") or [])]
            if commits:
                labels.extend(commit_labels(target, commits))
        return labels

    def run(self) -> list[Label]:
        labels: list[Label] = []
        for groups, rule_set in (
            (self.by_actor, rules.ACTOR_RULES),
            (self.by_repo, rules.REPO_RULES),
            (self.by_gist_owner, rules.GIST_OWNER_RULES),
        ):
            for target, items in groups.items():
                for rule in rule_set:
                    if label := rule(target, items, self.thresholds):
                        labels.append(label)
        labels.extend(self._commit_labels())
        labels.sort(key=lambda label: (-label.confidence, label.name, label.target))
        return labels
