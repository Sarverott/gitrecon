"""Commit messages as records: what kind of work a commit is, on what, and whether it breaks.

    parse_commit("feat(cli)!: add gitgraph\\n\\nBREAKING CHANGE: old flag removed")

The header is read with ``resources/grammars/humanish/commit.lark``: Conventional Commits,
git's merge and revert sentences, or ``plain``. What a type means is in ``resources/humanish.yml``.
"""

from __future__ import annotations

import subprocess
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from lark import Lark
from lark.exceptions import LarkError

from gitrecon.config import resource
from gitrecon.models import Label


@cache
def _parsers() -> tuple[Lark, Lark]:
    grammar = resource("grammars", "humanish", "commit.lark").read_text(encoding="utf-8")
    return Lark(grammar, start="header", parser="earley"), Lark(grammar, start="trailer", parser="earley")


@cache
def meanings() -> dict[str, Any]:
    return yaml.safe_load(resource("humanish.yml").read_text(encoding="utf-8"))


@dataclass
class ParsedCommit:
    form: str  # conventional | merge | revert | plain
    subject: str
    type: str | None = None  # feat, fix ... (lowercase)
    scope: str | None = None
    breaking: bool = False
    work: str | None = None  # feature | fix | documentation | upkeep | delivery (humanish.yml)
    trailers: dict[str, list[str]] = field(default_factory=dict)
    sha: str | None = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def parse_commit(message: str, sha: str | None = None) -> ParsedCommit:
    """One commit message -> its form, type, scope, subject, breaking mark and trailers."""
    header_parser, trailer_parser = _parsers()
    lines = message.strip().splitlines() or [""]
    header = lines[0].strip()
    commit = ParsedCommit(form="plain", subject=header, sha=sha)
    try:
        tree = header_parser.parse(header).children[0] if header else None
    except LarkError:
        tree = None
    if tree is not None:
        tokens = {token.type: str(token) for token in tree.children}
        commit.form = str(tree.data)
        commit.subject = tokens.get("SUBJECT", header).strip()
        if commit.form == "conventional":
            commit.type = tokens["TYPE"].lower()
            commit.scope = tokens.get("SCOPE")
            commit.breaking = "BREAKING" in tokens
            commit.work = (meanings()["commit_types"].get(commit.type) or {}).get("work")
        elif commit.form == "revert":
            commit.type, commit.work = "revert", "fix"
    for line in lines[1:]:
        try:
            key, value = (str(t) for t in trailer_parser.parse(line.strip()).children)
        except (LarkError, ValueError):
            continue
        commit.trailers.setdefault(key, []).append(value.strip())
        commit.breaking = commit.breaking or key.startswith("BREAKING")
    return commit


def read_commits(path: str | Path, max_commits: int | None = None) -> list[ParsedCommit]:
    """Parsed commits of every branch of the clone at ``path``, newest first."""
    args = ["git", "-C", str(Path(path).expanduser()), "log", "--branches", "--remotes", "--format=%H%x1f%B%x1e"]
    if max_commits:
        args.append(f"--max-count={max_commits}")
    done = subprocess.run(args, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip() or "git log failed")
    commits = []
    for entry in done.stdout.split("\x1e"):
        if "\x1f" in entry:
            sha, message = entry.strip().split("\x1f", 1)
            commits.append(parse_commit(message, sha=sha))
    return commits


def summarize_commits(commits: Iterable[ParsedCommit]) -> dict[str, Any]:
    """Counts by form, type, kind of work and scope; the share of own commits in conventional form."""
    commits = list(commits)
    own = [c for c in commits if c.form != "merge"]
    conventional = [c for c in own if c.form == "conventional"]
    return {
        "commits": len(commits),
        "own": len(own),
        "forms": dict(Counter(c.form for c in commits).most_common()),
        "conventional_share": round(len(conventional) / len(own), 3) if own else 0.0,
        "types": dict(Counter(c.type for c in conventional).most_common()),
        "work": dict(Counter(c.work or "unknown" for c in conventional).most_common()),
        "scopes": dict(Counter(c.scope for c in conventional if c.scope).most_common(15)),
        "breaking": sum(c.breaking for c in commits),
        "unknown_types": sorted({c.type for c in conventional if c.work is None}),
    }


def commit_labels(target: str, commits: Iterable[ParsedCommit]) -> list[Label]:
    """Labels a repository's (or an author's) commits support; thresholds in ``humanish.yml``."""
    commits = list(commits)
    summary = summarize_commits(commits)
    t = meanings()["commit_labels"]
    if summary["own"] < t["min_commits"]:
        return []
    labels = []
    evidence = lambda keep: [c.sha for c in commits if c.sha and keep(c)][:50]  # noqa: E731
    share = summary["conventional_share"]
    if share >= t["conventional_share"]:
        labels.append(Label("conventional-commits", target, round(share, 2), evidence(lambda c: c.form == "conventional"),
                            {"share": share, "threshold": t["conventional_share"], "own_commits": summary["own"]}))
    conventional = sum(summary["types"].values())
    fixes = summary["work"].get("fix", 0)
    if conventional >= t["min_commits"] and fixes / conventional >= t["fix_share"]:
        labels.append(Label("fix-heavy", target, round(fixes / conventional, 2), evidence(lambda c: c.work == "fix"),
                            {"fixes": fixes, "conventional": conventional, "threshold": t["fix_share"]}))
    bumps = summary["types"].get("bump", 0)
    if bumps >= t["releases"]:
        labels.append(Label("release-automation", target, 1.0, evidence(lambda c: c.type == "bump"),
                            {"releases": bumps, "threshold": t["releases"]}))
    if summary["breaking"]:
        labels.append(Label("breaking-changes", target, 1.0, evidence(lambda c: c.breaking),
                            {"breaking": summary["breaking"]}))
    return labels
