"""A repository's history across all branches, as a Mermaid ``gitGraph``.

    print(git_graph("~/__WORKSHOP/forge/redscope-technologies/gitrecon", max_commits=80))

Mermaid's gitGraph is a script (``commit``, ``branch``, ``checkout``, ``merge``) replayed in
order; git history is a graph of commits with parents. Turning one into the other takes two
decisions:

1. **Lanes** - which branch a commit is drawn on. Every branch claims the commits along its
   *first-parent* chain, in priority order (``master``/``main``, the BOS loop branches, then
   the rest), so a commit shared by several branches belongs to the most senior one. Commits
   that came in only through a merge of a branch that no longer exists get a lane named after
   the merge message (``Merge pull request #7 from user/feature`` -> ``feature``).
2. **Order** - parents before children (``git log --topo-order --reverse``). A lane is opened
   right after the commit it starts from, so branch points are exact.

Limits Mermaid sets: one root (extra roots are attached to the main lane), merges take one
other branch (octopus merges show their first two parents), and a merge is drawn from the
other lane's *current* head.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

SEP = "\x1f"
PRIORITY = ["master", "main", "trunk", "releasing", "testing", "revision", "development", "develop", "dev",
            "rejection"]
MERGE_SOURCE = [
    re.compile(r"^Merge pull request #\d+ from [^/\s]+/(\S+)"),
    re.compile(r"^Merge remote-tracking branch '(?:refs/remotes/)?([^']+)'"),  # keeps "origin/x"
    re.compile(r"^Merge branch '([^']+)'"),
    re.compile(r"^Merge branch (\S+)"),
]


@dataclass
class Commit:
    sha: str
    parents: list[str]
    time: int
    author: str
    subject: str
    tags: list[str] = field(default_factory=list)
    lane: str = ""

    @property
    def short(self) -> str:
        return self.sha[:7]


def _git(path: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip() or f"git {' '.join(args)} failed")
    return done.stdout


def read_history(path: str | Path, max_commits: int | None = None) -> list[Commit]:
    """Commits of every branch (local and remote), parents before children; newest ``max_commits``."""
    path = Path(path).expanduser()
    fmt = SEP.join(["%H", "%P", "%ct", "%an", "%s"])
    args = ["log", "--branches", "--remotes", "--topo-order", f"--format={fmt}"]
    if max_commits:
        args.append(f"--max-count={max_commits}")
    commits = []
    for line in _git(path, *args).splitlines():
        sha, parents, time, author, subject = line.split(SEP, 4)
        commits.append(Commit(sha, parents.split(), int(time), author, subject))
    commits.reverse()
    tags = _git(path, "for-each-ref", "refs/tags", f"--format=%(refname:short){SEP}%(objectname){SEP}%(*objectname)")
    by_sha = {c.sha: c for c in commits}
    for line in tags.splitlines():
        name, sha, peeled = line.split(SEP)
        if (commit := by_sha.get(peeled or sha)):
            commit.tags.append(name)
    return commits


def branch_tips(path: str | Path) -> dict[str, str]:
    """Branch name -> tip commit. A remote branch counts under its own name (``origin/x`` -> ``x``);
    when a local and a remote branch differ, the newer tip wins."""
    path = Path(path).expanduser()
    out = _git(path, "for-each-ref", "refs/heads", "refs/remotes",
               f"--format=%(refname){SEP}%(objectname){SEP}%(committerdate:unix)")
    tips: dict[str, tuple[int, str]] = {}
    for line in out.splitlines():
        ref, sha, time = line.split(SEP)
        if ref.startswith("refs/heads/"):
            name = ref.removeprefix("refs/heads/")
        else:
            name = ref.removeprefix("refs/remotes/").split("/", 1)[-1]
            if name == "HEAD":
                continue
        if name not in tips or int(time) > tips[name][0]:
            tips[name] = (int(time), sha)
    return {name: sha for name, (_, sha) in tips.items()}


def _priority(name: str) -> tuple[int, str]:
    return (PRIORITY.index(name) if name in PRIORITY else len(PRIORITY), name)


def assign_lanes(commits: list[Commit], tips: dict[str, str]) -> list[str]:
    """Set ``commit.lane`` for every commit; returns the lane names in the order they were claimed."""
    by_sha = {c.sha: c for c in commits}
    lanes: list[str] = []

    def claim(start: str, lane: str) -> bool:
        claimed, sha = False, start
        while sha in by_sha and not by_sha[sha].lane:
            by_sha[sha].lane = lane
            claimed = True
            parents = by_sha[sha].parents
            sha = parents[0] if parents else ""
        if claimed and lane not in lanes:
            lanes.append(lane)
        return claimed

    for name in sorted(tips, key=_priority):
        claim(tips[name], name)

    def unique(name: str) -> str:
        candidate, n = name, 2
        while candidate in lanes:
            candidate, n = f"{name}-{n}", n + 1
        return candidate

    # what only a merge brought in: lanes of branches that are gone, newest merge first
    for commit in reversed(commits):
        for parent in commit.parents[1:]:
            if parent in by_sha and not by_sha[parent].lane:
                source = next((m.group(1) for p in MERGE_SOURCE if (m := p.match(commit.subject))), None)
                claim(parent, unique(source or f"merged-{by_sha[parent].short}"))
    for commit in reversed(commits):  # anything left: unreachable through first parents or merges
        if not commit.lane:
            claim(commit.sha, unique(f"detached-{commit.short}"))
    return lanes


def _quote(text: str) -> str:
    return '"' + text.replace('"', "'") + '"'


def _commit_line(commit: Commit, labels: bool) -> str:
    label = commit.short
    if labels:
        subject = re.sub(r"\s+", " ", commit.subject)[:40].replace('"', "'")
        label = f"{commit.short} {subject}".strip()
    parts = [f"commit id:{_quote(label)}"]
    if commit.tags:
        parts.append(f"tag:{_quote(commit.tags[0])}")
    if commit.subject.startswith("Revert"):
        parts.append("type:REVERSE")
    elif len(commit.parents) > 1 or commit.subject.startswith("bump:"):
        parts.append("type:HIGHLIGHT")
    return " ".join(parts)


def render_gitgraph(commits: list[Commit], labels: bool = False, truncated: bool = False) -> str:
    """The Mermaid script for commits that already carry lanes (see :func:`assign_lanes`)."""
    if not commits:
        return "gitGraph\n"
    by_sha = {c.sha: c for c in commits}
    main = commits[0].lane
    # lanes opened right after the commit they start from: parent sha -> lanes
    opens: dict[str, list[str]] = {}
    first_of: dict[str, Commit] = {}
    for commit in commits:
        first_of.setdefault(commit.lane, commit)
    for lane, first in first_of.items():
        parent = first.parents[0] if first.parents else None
        if lane != main and parent in by_sha:
            opens.setdefault(parent, []).append(lane)

    lines = ["---", "config:", "  gitGraph:", f"    mainBranchName: {_quote(main)}",
             f"    showCommitLabel: {'true' if labels else 'false'}", "---", "gitGraph"]
    if truncated:
        lines.append(f"  %% the newest {len(commits)} commits; older history is not drawn")
    created, heads, current = {main}, {}, main

    def checkout(lane: str) -> None:
        nonlocal current
        if current != lane:
            lines.append(f"  checkout {_quote(lane)}")
            current = lane

    for commit in commits:
        lane = commit.lane
        if lane not in created:  # starts from a commit outside the drawing: hang it on the main lane
            checkout(main)
            lines.append(f"  branch {_quote(lane)}")
            created.add(lane)
            if main in heads:
                heads[lane] = heads[main]  # it starts with the main lane's head
            current = lane
        checkout(lane)
        other = next((by_sha[p].lane for p in commit.parents[1:] if p in by_sha and by_sha[p].lane != lane), None)
        # Mermaid refuses a merge when the other lane has nothing new for this one
        if other and other in heads and heads.get(lane) != heads[other]:
            merge = f"  merge {_quote(other)} id:{_quote(commit.short)}"
            if commit.tags:
                merge += f" tag:{_quote(commit.tags[0])}"
            lines.append(merge)
        else:
            lines.append("  " + _commit_line(commit, labels))
        heads[lane] = commit.sha
        for opened in opens.get(commit.sha, []):
            checkout(lane)
            lines.append(f"  branch {_quote(opened)}")
            created.add(opened)
            heads[opened] = commit.sha
            current = opened
    return "\n".join(lines) + "\n"


def git_graph(path: str | Path, max_commits: int | None = 150, labels: bool = False) -> str:
    """Mermaid gitGraph of the repository at ``path`` (all branches; the newest ``max_commits``)."""
    commits = read_history(path, max_commits)
    assign_lanes(commits, branch_tips(path))
    total = int(_git(Path(path).expanduser(), "rev-list", "--count", "--branches", "--remotes").strip() or 0)
    return render_gitgraph(commits, labels=labels, truncated=bool(max_commits) and total > len(commits))
