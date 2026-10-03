"""Harvesting links from notes (gists, markdown, notebooks, scripts) into a source catalog.

Every URL found is classified by what it can feed: GitHub API endpoints, feeds to
listen on, GitHub users / repos / gists to recon, URL patterns with placeholders
(``https://gist.github.com/{USER}.atom``) to expand, and plain sites.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

SCANNED_SUFFIXES = {".md", ".markdown", ".txt", ".py", ".ipynb", ".rst", ".html", ".json", ".yml", ".yaml"}
SKIPPED_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".ipynb_checkpoints"}

URL = re.compile(r"""https?://[^\s<>"'`\])|]+""")
PLACEHOLDER = re.compile(r"\$?\{[^}]*\}")
TRAILING = ".,;:!?*"

# Paths on github.com that are site sections, not users.
GITHUB_RESERVED = {
    "about", "apps", "collections", "contact", "customer-stories", "enterprise", "explore",
    "features", "login", "marketplace", "new", "notifications", "orgs", "pricing", "pulls",
    "issues", "search", "security", "settings", "site", "sponsors", "topics", "trending",
}


@dataclass
class Link:
    url: str
    kind: str
    domain: str
    found_in: list[str] = field(default_factory=list)  # "path:line"

    def to_dict(self) -> dict:
        return asdict(self)


def clean_url(url: str) -> str:
    url = url.rstrip(TRAILING)
    # markdown leftovers: "url)" was cut by the regex, "**" or "_" emphasis around it
    return url.rstrip("*_")


def classify(url: str) -> str:
    if PLACEHOLDER.search(url):
        return "pattern"
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    path = [p for p in parts.path.split("/") if p]
    lowered = url.lower()
    if lowered.endswith((".atom", ".rss", "rss.xml", "/feed", "/feed/", ".xml")) and (
        "feed" in lowered or "atom" in lowered or "rss" in lowered
    ):
        return "feed"
    if host == "api.github.com":
        return "github-api"
    if host == "gist.github.com":
        return "gist" if len(path) >= 2 or (path and len(path[0]) >= 20) else "github-user"
    if host == "github.com":
        if not path or path[0] in GITHUB_RESERVED:
            return "github-site"
        return "github-repo" if len(path) >= 2 else "github-user"
    if host.endswith(".github.io"):
        return "github-pages"
    if host in {"huggingface.co", "www.kaggle.com", "kaggle.com"}:
        return "dataset-hub"
    if host.endswith("wikipedia.org") or host == "www.wikidata.org":
        return "wiki"
    if host in {"pypi.org", "npmjs.org", "www.npmjs.com", "npmjs.com", "rubygems.org", "www.jsdelivr.com"}:
        return "package-registry"
    if host.startswith(("share.google", "www.google.")):
        return "search"
    return "site"


def _texts(path: Path) -> Iterator[tuple[int, str]]:
    """(line number, text) pairs; notebooks yield their cell sources, not the JSON."""
    if path.suffix == ".ipynb":
        try:
            cells = json.loads(path.read_text(encoding="utf-8")).get("cells", [])
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        for index, cell in enumerate(cells):
            yield index + 1, "".join(cell.get("source", []))
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return
    yield from enumerate(lines, start=1)


def scan_file(path: Path, label: str | None = None) -> Iterator[tuple[str, str]]:
    """(url, "label:line") for every URL in the file."""
    label = label or str(path)
    for line_no, text in _texts(path):
        for match in URL.finditer(text):
            url = clean_url(match.group())
            if urlsplit(url).hostname:
                yield url, f"{label}:{line_no}"


def iter_files(root: Path, exclude: Iterable[Path] = ()) -> Iterator[Path]:
    excluded = [p.resolve() for p in exclude]
    for path in sorted(root.rglob("*")):
        if any(part in SKIPPED_DIRS for part in path.parts):
            continue
        resolved = path.resolve()
        if any(resolved == e or e in resolved.parents for e in excluded):
            continue
        if path.is_file() and path.suffix.lower() in SCANNED_SUFFIXES:
            yield path


def harvest(root: Path, exclude: Iterable[Path] = ()) -> list[Link]:
    """All distinct links under ``root``, each with every place it was found."""
    root = Path(root)
    found: dict[str, Link] = {}
    for path in iter_files(root, exclude):
        for url, where in scan_file(path, str(path.relative_to(root))):
            link = found.get(url)
            if link is None:
                link = found[url] = Link(url, classify(url), (urlsplit(url).hostname or "").lower())
            link.found_in.append(where)
    return sorted(found.values(), key=lambda link: (link.kind, link.url))


def expand_pattern(url: str, **values: str) -> str:
    """Fill ``{USER}`` / ``${EACHDIR}`` style placeholders (case-insensitive names)."""
    lowered = {k.lower(): v for k, v in values.items()}

    def fill(match: re.Match) -> str:
        name = match.group().lstrip("$").strip("{}").lower()
        return lowered.get(name, match.group())

    return PLACEHOLDER.sub(fill, url)


def git_remote(directory: Path) -> str | None:
    """``origin`` URL of a cloned repository, read straight from ``.git/config``."""
    config = Path(directory) / ".git" / "config"
    if not config.is_file():
        return None
    match = re.search(r'\[remote "origin"\][^\[]*?url\s*=\s*(\S+)', config.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def gist_clones(root: Path) -> list[Path]:
    """Directories directly under ``root`` that are clones of gists."""
    return sorted(
        d for d in Path(root).iterdir()
        if d.is_dir() and "gist.github.com" in (git_remote(d) or "")
    )


def harvest_gists(root: Path) -> list[Link]:
    """Links from every gist clone under ``root`` (sources labelled ``<gist id>/<file>``)."""
    found: dict[str, Link] = {}
    for clone in gist_clones(root):
        for link in harvest(clone):
            merged = found.setdefault(link.url, Link(link.url, link.kind, link.domain))
            merged.found_in += [f"{clone.name}/{where}" for where in link.found_in]
    return sorted(found.values(), key=lambda link: (link.kind, link.url))


def save_catalog(links: Iterable[Link], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for link in links:
            fh.write(json.dumps(link.to_dict(), ensure_ascii=False) + "\n")
    return path


def load_catalog(path: Path) -> list[Link]:
    with path.open(encoding="utf-8") as fh:
        return [Link(**json.loads(line)) for line in fh if line.strip()]
