"""Who made a repository, read from its git log: commits, lines, first and last day.

    people = contributors("~/__WORKSHOP/forge/rattish/mit-license")

One person often appears under several names and addresses. Git's own ``.mailmap`` is
honoured, and records that share an address or a name are joined. An *ignorelist*
(``resources/ignorelist.txt`` by default: bots) removes identities before anything is
counted for display - listings, the AUTHORS text, the pie, the band of ``gitrecon score``.
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import cache
from pathlib import Path
from typing import Any

from gitrecon.config import resource

RECORD, FIELD, LIST = "\x1e", "\x1f", "\x1d"


@dataclass
class Contributor:
    name: str
    emails: list[str] = field(default_factory=list)  # the most used first
    names: list[str] = field(default_factory=list)  # other spellings met
    commits: int = 0
    merges: int = 0
    added: int = 0
    deleted: int = 0
    co_authored: int = 0  # commits of others naming this person in Co-authored-by
    first: int = 0  # unix time of the first commit
    last: int = 0

    def to_json(self) -> dict[str, Any]:
        day = lambda t: datetime.fromtimestamp(t, timezone.utc).date().isoformat() if t else None  # noqa: E731
        return {"name": self.name, "emails": self.emails, "names": self.names, "commits": self.commits,
                "merges": self.merges, "added": self.added, "deleted": self.deleted,
                "co_authored": self.co_authored, "first": day(self.first), "last": day(self.last)}


def read_ignorelist(path: str | Path | None = None) -> list[str]:
    """Patterns of an ignorelist file (default: ``resources/ignorelist.txt``), lowercase."""
    source = Path(path).expanduser() if path else resource("ignorelist.txt")
    lines = source.read_text(encoding="utf-8").splitlines()
    return [line.strip().lower() for line in lines if line.strip() and not line.lstrip().startswith("#")]


@cache
def _matcher(pattern: str) -> re.Pattern:
    # only * and ? are wildcards: "[bot]" in a name is three plain characters, not a character class
    return re.compile(re.escape(pattern).replace(r"\*", ".*").replace(r"\?", "."), re.DOTALL)


def is_ignored(patterns: list[str], *identities: str) -> bool:
    """Whether any of the names / addresses matches a pattern of the ignorelist."""
    return any(_matcher(pattern).fullmatch(identity.lower()) for identity in identities if identity
               for pattern in patterns)


def _log(path: Path, max_commits: int | None) -> str:
    fmt = RECORD + FIELD.join(["%H", "%aN", "%aE", "%at", "%P",
                               f"%(trailers:key=Co-authored-by,valueonly,separator={LIST})"])
    args = ["git", "-C", str(path), "log", "--branches", "--remotes", "--use-mailmap", "--numstat", f"--format={fmt}"]
    if max_commits:
        args.append(f"--max-count={max_commits}")
    done = subprocess.run(args, capture_output=True, text=True, check=False, errors="replace")
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip() or "git log failed")
    return done.stdout


def contributors(path: str | Path, max_commits: int | None = None, ignore: list[str] | None = None) -> list[Contributor]:
    """Contributors of every branch of the clone at ``path``, most commits first."""
    by_key: dict[str, str] = {}  # an address or a lowercase name -> group id
    groups: dict[str, dict[str, Any]] = {}

    def group(name: str, email: str) -> dict[str, Any]:
        keys = [k for k in (email.lower(), "name:" + name.lower()) if k not in ("", "name:")]
        found = list(dict.fromkeys(by_key[k] for k in keys if k in by_key))
        target = found[0] if found else (keys[0] if keys else "unknown")
        entry = groups.setdefault(target, {"names": Counter(), "emails": Counter(), "commits": 0, "merges": 0,
                                           "added": 0, "deleted": 0, "co_authored": 0, "first": 0, "last": 0})
        for other in found[1:]:  # the same person met under two records: join them
            merged = groups.pop(other)
            for key in ("names", "emails"):
                entry[key].update(merged[key])
            for key in ("commits", "merges", "added", "deleted", "co_authored"):
                entry[key] += merged[key]
            entry["first"] = min(t for t in (entry["first"], merged["first"]) if t) if entry["first"] or merged["first"] else 0
            entry["last"] = max(entry["last"], merged["last"])
            for k, v in list(by_key.items()):
                if v == other:
                    by_key[k] = target
        for k in keys:
            by_key[k] = target
        return entry

    for record in _log(Path(path).expanduser(), max_commits).split(RECORD)[1:]:
        header, _, stats = record.partition("\n")
        _sha, name, email, time, parents, trailers = (header.split(FIELD) + [""] * 6)[:6]
        entry = group(name, email)
        entry["names"][name] += 1
        if email:
            entry["emails"][email.lower()] += 1
        when = int(time or 0)
        entry["first"] = min(entry["first"], when) if entry["first"] else when
        entry["last"] = max(entry["last"], when)
        if len(parents.split()) > 1:
            entry["merges"] += 1
        else:
            entry["commits"] += 1
        for line in stats.splitlines():
            added, _, rest = line.partition("\t")
            deleted = rest.partition("\t")[0]
            if added.isdigit() and deleted.isdigit():
                entry["added"] += int(added)
                entry["deleted"] += int(deleted)
        for value in filter(None, (v.strip() for v in trailers.split(LIST))):
            co_name, _, co_email = value.partition("<")
            other = group(co_name.strip(), co_email.rstrip("> ").strip())
            if other is not entry:
                other["co_authored"] += 1
                other["names"][co_name.strip()] += 0  # known, without counting it as the usual spelling
                if co_email.rstrip("> ").strip():
                    other["emails"][co_email.rstrip("> ").strip().lower()] += 0

    people = []
    for entry in groups.values():
        names = [n for n, _ in entry["names"].most_common() if n]
        emails = [e for e, _ in entry["emails"].most_common()]
        if ignore and is_ignored(ignore, *names, *emails):
            continue
        people.append(Contributor(names[0] if names else (emails[0] if emails else "unknown"), emails, names[1:],
                                  entry["commits"], entry["merges"], entry["added"], entry["deleted"],
                                  entry["co_authored"], entry["first"], entry["last"]))
    people.sort(key=lambda c: (-(c.commits + c.merges), -c.added, c.name.lower()))
    return people


def authors_text(people: list[Contributor], repository: str = "") -> str:
    """The text of an AUTHORS file: one ``Name <address>`` per line, most commits first."""
    lines = [f"# Authors of {repository}".rstrip() + ", in order of the number of commits.",
             "# Generated by `gitrecon contributors --format authors` from the git history.", ""]
    for person in people:
        if person.commits + person.merges + person.co_authored:
            lines.append(f"{person.name} <{person.emails[0]}>" if person.emails else person.name)
    return "\n".join(lines) + "\n"


def pie(shares: dict[str, float], title: str, top: int = 12) -> str:
    """A Mermaid pie of ``label -> amount``; what does not fit in ``top`` slices becomes ``others``."""
    ranked = sorted(((label, amount) for label, amount in shares.items() if amount > 0), key=lambda kv: (-kv[1], kv[0]))
    shown, rest = ranked[:top], ranked[top:]
    if rest:
        shown.append((f"others ({len(rest)})", sum(amount for _, amount in rest)))
    clean = lambda text: text.replace('"', "'")  # noqa: E731
    lines = ["pie showData", f"    title {clean(title)}"]
    lines += [f'    "{clean(label)}" : {amount:g}' for label, amount in shown]
    return "\n".join(lines) + "\n"


def contributors_pie(people: list[Contributor], repository: str, by: str = "commits", top: int = 12) -> str:
    amount = {"commits": lambda c: c.commits + c.merges, "lines": lambda c: c.added + c.deleted,
              "added": lambda c: c.added}[by]
    what = {"commits": "Commits", "lines": "Lines changed", "added": "Lines added"}[by]
    return pie({person.name: amount(person) for person in people}, f"{what} in {repository} by contributor", top)
