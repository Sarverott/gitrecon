"""Writing gitrecon findings into the map (``datasets/imperialmap``).

Writes are deterministic (sorted keys, stable order), so re-running an update
without new findings changes nothing and pushes no noise to the Hub.

- dnstrees/<reversed domain>/.holders.yml   links seen on that domain + their unions
- ip-address-records/<v4|v6>/.../.index.json networks with the services behind them
- host-unions/<union>/.index.json           relations: url -> domain, domain/ip -> service
- <area>/.index.json                         recursive listing of the area
"""

from __future__ import annotations

import ipaddress
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from gitrecon.atlas.paths import DNSTREES, HOST_UNIONS, IP_RECORDS, domain_path, ip_path
from gitrecon.sources.links import Link

# GitHub /meta keys holding CIDR lists; "actions" alone is thousands of ranges.
META_HEAVY = {"actions", "actions_macos"}


def _is_network(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        ipaddress.ip_network(value, strict=False)
    except ValueError:
        return False
    return True


def _write_json(path: Path, data: Any) -> bool:
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return _write_text(path, text)


def _write_text(path: Path, text: str) -> bool:
    """Write only when content differs; True when the file changed."""
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


@dataclass
class AtlasUpdate:
    root: Path
    changed: list[Path] = field(default_factory=list)

    def _track(self, path: Path, did_change: bool) -> None:
        if did_change:
            self.changed.append(path)

    # --- links -> dnstrees + host-unions ------------------------------------

    def add_links(self, links: Iterable[Link], union: str) -> None:
        by_domain: dict[str, list[Link]] = defaultdict(list)
        for link in links:
            if link.domain and link.kind != "pattern":
                by_domain[link.domain].append(link)

        for domain, domain_links in by_domain.items():
            node = self.root / DNSTREES / domain_path(domain) / ".holders.yml"
            holders = self._read_yaml(node)
            unions = set(holders.get("unions", [])) | {f"{HOST_UNIONS}/{union}"}
            urls = set(holders.get("links", [])) | {link.url for link in domain_links}
            text = yaml.safe_dump(
                {"domain": domain, "unions": sorted(unions), "links": sorted(urls)},
                sort_keys=False, allow_unicode=True,
            )
            self._track(node, _write_text(node, text))

        relations = [
            {"url": link.url, "kind": link.kind, "domain": link.domain, "found_in": sorted(link.found_in)}
            for links_ in by_domain.values() for link in links_
        ]
        relations.sort(key=lambda r: r["url"])
        path = self.root / HOST_UNIONS / union / ".index.json"
        self._track(path, _write_json(path, {"union": union, "relations": relations}))

    # --- GitHub /meta -> ip-address-records + host-unions -------------------

    def add_github_meta(self, meta: dict[str, Any], include_heavy: bool = False) -> None:
        networks: dict[str, set[str]] = defaultdict(set)
        for service, value in meta.items():
            if service in META_HEAVY and not include_heavy:
                continue
            if isinstance(value, list) and value and all(_is_network(v) for v in value):
                for cidr in value:
                    networks[cidr].add(service)

        by_node: dict[Path, dict[str, set[str]]] = defaultdict(dict)
        for cidr, services in networks.items():
            by_node[self.root / IP_RECORDS / ip_path(cidr) / ".index.json"][cidr] = services
        for path, cidrs in by_node.items():
            data = {
                "cidrs": {cidr: sorted(services) for cidr, services in sorted(cidrs.items())},
                "union": f"{HOST_UNIONS}/github-meta",
                "source": "https://api.github.com/meta",
            }
            self._track(path, _write_json(path, data))

        domains = meta.get("domains", {})
        union = {
            "union": "github-meta",
            "source": "https://api.github.com/meta",
            "domains": {k: sorted(v) for k, v in sorted(domains.items()) if isinstance(v, list)},
            "services": {
                service: len([c for c, s in networks.items() if service in s])
                for service in sorted({s for services in networks.values() for s in services})
            },
            "skipped": [] if include_heavy else sorted(META_HEAVY),
        }
        path = self.root / HOST_UNIONS / "github-meta" / ".index.json"
        self._track(path, _write_json(path, union))

    # --- listings -----------------------------------------------------------

    def reindex(self, areas: Iterable[str] = (DNSTREES, IP_RECORDS, HOST_UNIONS)) -> None:
        """Rewrite ``<area>/.index.json``: every file under the area, recursively."""
        for area in areas:
            base = self.root / area
            if not base.exists():
                continue
            files = sorted(
                p.relative_to(base).as_posix()
                for p in base.rglob("*")
                if p.is_file() and p != base / ".index.json"
            )
            path = base / ".index.json"
            self._track(path, _write_json(path, {"area": area, "files": files}))

    @staticmethod
    def _read_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
