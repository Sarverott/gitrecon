"""Start, stop and list the services of services/<group>/ - with their dependencies.

Every service has two profiles: its group and its own name (``[automations, n8n]``).
Compose leaves services of disabled profiles out entirely, so ``up n8n`` alone would not
find ``postgres``. This script reads the fully resolved model (``docker compose config``),
follows ``depends_on`` and enables exactly the profiles the targets need.

    python services/control.py list
    python services/control.py up n8n gitea          # services, or whole groups:
    python services/control.py up databases internals
    python services/control.py up runners --dry-run  # anything after the targets goes to compose
    python services/control.py down | ps | logs SERVICE
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # compose.yaml lives at the repository root


def compose(*args: str, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", *args], cwd=ROOT, check=False, text=True,
                          capture_output=capture)


def model() -> dict:
    done = compose("--profile", "*", "config", "--format", "json", capture=True)
    if done.returncode != 0:
        sys.exit(done.stderr.strip())
    return json.loads(done.stdout)["services"]


def group(service: dict) -> str:
    profiles = service.get("profiles") or []
    return profiles[0] if profiles else "gitrecon"


def resolve(targets: list[str], services: dict) -> list[str]:
    """Targets (service or group names) and everything they depend on, in a stable order."""
    chosen = [name for name, svc in services.items() if name in targets or group(svc) in targets]
    unknown = [t for t in targets if t not in services and t not in {group(s) for s in services.values()}]
    if unknown:
        sys.exit(f"unknown service or group: {', '.join(unknown)} (see: list)")
    queue, seen = list(chosen), []
    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.append(name)
        queue += list((services[name].get("depends_on") or {}).keys())
    return seen


def profile_args(names: list[str], services: dict) -> list[str]:
    args = []
    for name in names:
        for profile in services[name].get("profiles") or []:
            if profile == name:  # the service's own profile enables just that service
                args += ["--profile", profile]
    return args


def runner_token(names: list[str]) -> None:
    """The GitHub runner needs a token at start; borrow the gh CLI login unless one is set."""
    if "github-runner" in names and not os.environ.get("GITHUB_RUNNER_TOKEN") and shutil.which("gh"):
        token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False).stdout.strip()
        if token:
            os.environ["GITHUB_RUNNER_TOKEN"] = token


def cmd_up(argv: list[str]) -> int:
    targets = [a for a in argv if not a.startswith("-")]
    extra = [a for a in argv if a.startswith("-")]
    if not targets:
        sys.exit("up needs services or groups, e.g. up databases n8n (see: list)")
    services = model()
    names = resolve(targets, services)
    runner_token(names)
    print(f"starting: {', '.join(names)}", file=sys.stderr)
    return compose(*profile_args(names, services), "up", "-d", *extra, *names).returncode


def cmd_list(argv: list[str]) -> int:
    services = model()
    rows = []
    for name, svc in sorted(services.items(), key=lambda kv: (group(kv[1]), kv[0])):
        ports = ", ".join(
            f"{p.get('host_ip', '')}:{p['published']}->{p['target']}" + ("/udp" if p.get("protocol") == "udp" else "")
            for p in svc.get("ports") or [] if p.get("published")
        )
        image = svc.get("image") or "(build)"
        needs = ", ".join((svc.get("depends_on") or {}).keys())
        rows.append((group(svc), name, image, ports, needs))
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        for row in rows:
            print("  ".join(row))
        return 0
    table = Table("group", "service", "image", "published", "needs", header_style="bold magenta", box=None)
    current = None
    for row in rows:
        table.add_row(*(f"[bold red]{row[0]}[/]" if row[0] != current else "", *row[1:]))
        current = row[0]
    Console().print(table)
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    command, rest = argv[0], argv[1:]
    match command:
        case "up":
            return cmd_up(rest)
        case "list":
            return cmd_list(rest)
        case "down":
            return compose("--profile", "*", "down", *rest).returncode
        case "ps":
            return compose("--profile", "*", "ps", *rest).returncode
        case "logs":
            return compose("--profile", "*", "logs", "--tail", "100", "-f", *rest).returncode
        case "pull":
            services = model()
            names = resolve(rest, services) if rest else list(services)
            return compose(*profile_args(names, services), "pull", "--ignore-buildable", *names).returncode
    sys.exit(f"unknown command {command!r}\n{__doc__}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
