"""user-namespace of the map, per ``datasets/imperialmap/user-namespace/README.md``.

A username on a platform becomes one identity file::

    user-namespace/NS/<a12y(username)>/<a12y(platform)>/<md5>.json
    UserName on github.com -> NS/u8e/g6-3m/6784ce76fa5dbf3d7e73f94cc2df055f.json

- ``a12y(username)``: numeronym of the lowercased name (``username`` -> ``u8e``)
- ``a12y(platform)``: first char, label lengths joined by ``-``, last char
  (``github.com`` -> ``g6-3m``)
- ``md5``: of ``"username@platform\\n"`` lowercased - exactly what
  ``echo "username@github.com" | md5sum`` prints, which is how the README example
  was made.

``user-namespace/index.json`` maps each username to its identity files. Identities
of one person (profile, mail, other platforms) point at each other in ``sibiling``.
Paths stay in full form; shortening to the bare hash once no collision shows up
is left for later, as the README says.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlsplit

from gitrecon.models.star import Star
from gitrecon.sources.links import Link
from gitrecon.text.a12y import a12y_key

USER_NAMESPACE = "user-namespace"
NS_DIR = "NS"
INDEX = "index.json"


def name_a12y(username: str) -> str:
    return a12y_key(username.lower())


def platform_a12y(platform: str) -> str:
    """``github.com`` -> ``g6-3m``; ``gist.github.com`` -> ``g4-6-3m``."""
    labels = [label for label in platform.lower().strip(".").split(".") if label]
    if not labels:
        raise ValueError(f"not a platform domain: {platform!r}")
    joined = ".".join(labels)
    return f"{joined[0]}{'-'.join(str(len(label)) for label in labels)}{joined[-1]}"


def identity_hash(username: str, platform: str) -> str:
    return hashlib.md5(f"{username}@{platform}\n".lower().encode("utf-8")).hexdigest()


def identity_path(username: str, platform: str) -> PurePosixPath:
    """Path relative to ``user-namespace/NS`` - the form used in ``index.json`` and ``sibiling``."""
    return PurePosixPath(
        name_a12y(username), platform_a12y(platform), f"{identity_hash(username, platform)}.json"
    )


@dataclass
class Identity:
    user: str
    platform: str
    type: str = "profile"  # "profile" | "mail" | ...
    sibiling: list[str] = field(default_factory=list)  # spelled as in the dataset README
    description: str = ""

    @property
    def path(self) -> PurePosixPath:
        return identity_path(self.user, self.platform)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user": self.user,
            "platform": self.platform,
            "type": self.type,
            "sibiling": sorted(set(self.sibiling)),
            "description": self.description,
        }


@dataclass
class UserNamespace:
    """Reads, merges and writes identities under ``<map root>/user-namespace``.

    Identity files are written as they are added; ``index.json`` on :meth:`flush`.
    """

    map_root: Path
    changed: list[Path] = field(default_factory=list)
    _index: dict[str, list[str]] | None = field(default=None, repr=False)

    @property
    def base(self) -> Path:
        return self.map_root / USER_NAMESPACE

    def _file(self, rel: PurePosixPath | str) -> Path:
        return self.base / NS_DIR / rel

    def load(self, user: str, platform: str) -> Identity | None:
        path = self._file(identity_path(user, platform))
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Identity(**{k: data.get(k, v) for k, v in Identity(user, platform).to_dict().items()})

    def add(self, identity: Identity) -> Identity:
        """Write an identity, merging siblings and keeping a known description."""
        existing = self.load(identity.user, identity.platform)
        if existing:
            identity.sibiling = sorted(set(existing.sibiling) | set(identity.sibiling))
            identity.description = identity.description or existing.description
        self._write(self._file(identity.path), identity.to_dict())
        self._index_add(identity.user, str(identity.path))
        return identity

    def link(self, a: Identity, b: Identity) -> None:
        """Make two identities siblings of each other (both files updated)."""
        a.sibiling = sorted(set(a.sibiling) | {str(b.path)})
        b.sibiling = sorted(set(b.sibiling) | {str(a.path)})
        self.add(a)
        self.add(b)

    def index(self) -> dict[str, list[str]]:
        """``index.json`` content, loaded once and kept in memory until :meth:`flush`."""
        if self._index is None:
            path = self.base / INDEX
            self._index = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        return self._index

    def _index_add(self, user: str, rel: str) -> None:
        index = self.index()
        index[user] = sorted(set(index.get(user, [])) | {rel})

    def flush(self) -> None:
        """Write ``index.json`` (call once after adding identities)."""
        if self._index is not None:
            ordered = dict(sorted(self._index.items(), key=lambda kv: (kv[0].lower(), kv[0])))
            self._write(self.base / INDEX, ordered)

    def _write(self, path: Path, data: Any) -> None:
        text = json.dumps(data, indent=4, ensure_ascii=False) + "\n"
        if path.exists() and path.read_text(encoding="utf-8") == text:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.changed.append(path)


# --- filling the namespace from what gitrecon collects ----------------------

GITHUB = "github.com"
GIST = "gist.github.com"


def github_owner_identities(stars: Iterable[Star]) -> list[Identity]:
    """Public GitHub accounts owning the starred repositories (users and organizations)."""
    owners: dict[str, Identity] = {}
    for star in stars:
        owner = (star.repo.raw.get("owner") or {}) if star.repo.raw else {}
        login = owner.get("login") or star.repo.owner
        if not login or login.lower() in owners:
            continue
        kind = "organization" if owner.get("type") == "Organization" else "user"
        owners[login.lower()] = Identity(login, GITHUB, "profile", description=f"github {kind}")
    return list(owners.values())


def link_identities(links: Iterable[Link]) -> list[tuple[Identity, Identity | None]]:
    """GitHub accounts named in harvested links; a gist author also gets their gist profile.

    Returns ``(github profile, gist profile or None)`` pairs - a pair is one person.
    """
    found: dict[str, tuple[Identity, Identity | None]] = {}
    for link in links:
        parts = [p for p in urlsplit(link.url).path.split("/") if p]
        if link.kind in ("github-user", "github-repo") and link.domain == GITHUB and parts:
            login = parts[0]
            found.setdefault(login.lower(), (Identity(login, GITHUB, description="seen in gist harvest"), None))
        elif link.kind == "gist" and link.domain == GIST and len(parts) >= 2:
            login = parts[0]
            profile, _ = found.get(login.lower(), (Identity(login, GITHUB, description="gist author"), None))
            found[login.lower()] = (profile, Identity(login, GIST, description="gists of the github account"))
    return list(found.values())
