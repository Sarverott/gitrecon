"""Start, stop, list and check the services of services/<group>/ - with their dependencies.

Every service has two profiles: its group and its own name (``[automations, n8n]``).
Compose leaves services of disabled profiles out entirely, so ``up n8n`` alone would not
find ``postgres``. This script reads the fully resolved model (``docker compose config``),
follows ``depends_on`` and enables exactly the profiles the targets need.

Volumes are bind mounts of ``datasets/_dockdrives/<volume>`` (``volumes.compose.yaml``);
``up`` creates the folders its services need, ``drives`` checks them all, ``backup``
archives them (from inside a container: services write as their own users).

What compose does (resolving includes and profiles, up, down, pull, logs) goes through the
``docker compose`` command - neither the docker nor the podman Python package speaks
compose. What the engine answers directly (containers, volumes) goes through the docker
SDK, or podman's when no docker socket answers.

    python services/control.py list
    python services/control.py up n8n gitea          # services, or whole groups:
    python services/control.py up databases internals
    python services/control.py up runners --dry-run  # options after the targets go to compose
    python services/control.py ps | drives | down | logs SERVICE | pull [TARGETS]
    python services/control.py backup [VOLUMES] [--live]   # -> datasets/_backups/*.tar.gz
    python services/control.py env                         # regenerate services/.env.example
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # compose.yaml lives at the repository root
PROJECT = "gitrecon"
DOCKDRIVES = ROOT / "datasets" / "_dockdrives"

os.environ.setdefault("REPO_DIR", str(ROOT))  # volumes.compose.yaml binds ${REPO_DIR}/datasets/_dockdrives


# --- compose (CLI) -----------------------------------------------------------------


def compose(*args: str, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", *args], cwd=ROOT, check=False, text=True,
                          capture_output=capture)


def config() -> dict:
    done = compose("--profile", "*", "config", "--format", "json", capture=True)
    if done.returncode != 0:
        sys.exit(done.stderr.strip())
    return json.loads(done.stdout)


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


# --- volumes as folders -------------------------------------------------------------


def drive_volumes(services: dict, names: list[str] | None = None) -> dict[str, list[str]]:
    """Named volumes -> the services mounting them (all services, or just ``names``)."""
    used: dict[str, list[str]] = {}
    for name, svc in services.items():
        if names is not None and name not in names:
            continue
        for mount in svc.get("volumes") or []:
            if mount.get("type") == "volume" and mount.get("source"):
                used.setdefault(mount["source"], []).append(name)
    return used


def drive_path(volume: dict) -> Path | None:
    device = (volume.get("driver_opts") or {}).get("device")
    return Path(device) if device else None


def ensure_drives(model: dict, names: list[str]) -> None:
    for volume in drive_volumes(model["services"], names):
        path = drive_path(model["volumes"].get(volume, {}))
        if path and not path.exists():
            path.mkdir(parents=True)
            print(f"created {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}", file=sys.stderr)


def folder_size(path: Path) -> int | None:
    """Bytes under ``path``; ``None`` when a container user owns it (postgres: uid 70, mode 700)."""
    if not os.access(path, os.R_OK | os.X_OK):
        return None
    total = 0
    try:
        for entry in path.rglob("*"):
            try:
                if entry.is_file() and not entry.is_symlink():
                    total += entry.stat().st_size
            except OSError:
                continue
    except PermissionError:
        return None  # owned by a container user
    return total


# --- engine (SDK) -------------------------------------------------------------------


def engine():
    """A docker SDK client, or podman's (same interface for what we use), or None."""
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return client
    except Exception:  # noqa: BLE001 - any failure means "try the next engine"
        pass
    try:
        from podman import PodmanClient

        client = PodmanClient()
        client.ping()
        return client
    except Exception:  # noqa: BLE001
        return None


def project_containers(client) -> list:
    return client.containers.list(all=True, filters={"label": f"com.docker.compose.project={PROJECT}"})


def project_volumes(client) -> dict[str, dict]:
    """Engine-side volumes of the project: compose name -> attributes."""
    found = {}
    for volume in client.volumes.list(filters={"label": f"com.docker.compose.project={PROJECT}"}):
        name = volume.attrs.get("Labels", {}).get("com.docker.compose.volume") or volume.name
        found[name] = volume.attrs
    return found


# --- commands ----------------------------------------------------------------------


def _table(*columns: str):
    from rich.table import Table

    return Table(*columns, header_style="bold magenta", box=None)


def _print(renderable) -> None:
    from rich.console import Console

    Console().print(renderable)


def cmd_up(argv: list[str]) -> int:
    targets = [a for a in argv if not a.startswith("-")]
    extra = [a for a in argv if a.startswith("-")]
    if not targets:
        sys.exit("up needs services or groups, e.g. up databases n8n (see: list)")
    model = config()
    names = resolve(targets, model["services"])
    if "github-runner" in names and not os.environ.get("GITHUB_RUNNER_TOKEN") and shutil.which("gh"):
        token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False).stdout.strip()
        if token:
            os.environ["GITHUB_RUNNER_TOKEN"] = token  # the runner needs it at start
    if "--dry-run" not in extra:
        ensure_drives(model, names)
    print(f"starting: {', '.join(names)}", file=sys.stderr)
    return compose(*profile_args(names, model["services"]), "up", "-d", *extra, *names).returncode


HOST_RULE = re.compile(r"Host\(`([^`]+)`\)")


def routes(service: dict) -> list[str]:
    """Addresses traefik gives the service: the first Host() of each router (gateway URLs)."""
    labels = service.get("labels") or {}
    found = []
    for key, value in labels.items():
        if key.startswith("traefik.http.routers.") and key.endswith(".rule"):
            hosts = HOST_RULE.findall(value)
            if hosts:
                found.append(hosts[0])
    return found


def cmd_list(argv: list[str]) -> int:
    services = config()["services"]
    table = _table("group", "service", "address (via traefik)", "published on host", "needs")
    current = None
    for name, svc in sorted(services.items(), key=lambda kv: (group(kv[1]), kv[0])):
        ports = ", ".join(
            f"{p.get('host_ip', '')}:{p['published']}->{p['target']}" + ("/udp" if p.get("protocol") == "udp" else "")
            for p in svc.get("ports") or [] if p.get("published")
        )
        needs = ", ".join((svc.get("depends_on") or {}).keys())
        label = f"[bold red]{group(svc)}[/]" if group(svc) != current else ""
        public = any((svc.get("labels") or {}).get(k) == "public" for k in (svc.get("labels") or {}) if k.endswith(".entrypoints"))
        address = ", ".join(routes(svc)) + (" [yellow](+ public)[/]" if public else "")
        table.add_row(label, name, address or "[grey58]internal only[/]", ports, needs)
        current = group(svc)
    _print(table)
    return 0


def cmd_ps(argv: list[str]) -> int:
    client = engine()
    if client is None:
        return compose("--profile", "*", "ps", *argv).returncode
    table = _table("service", "state", "health", "image", "ports")
    for container in sorted(project_containers(client), key=lambda c: c.labels.get("com.docker.compose.service", "")):
        state = container.attrs.get("State", {})
        status = state.get("Status", container.status)
        health = (state.get("Health") or {}).get("Status", "-")
        colour = "green" if status == "running" else "yellow" if status in ("restarting", "created") else "red"
        ports = ", ".join(
            f"{b[0].get('HostIp', '')}:{b[0]['HostPort']}->{port}"
            for port, b in (container.attrs.get("NetworkSettings", {}).get("Ports") or {}).items() if b
        )
        image = (container.attrs.get("Config") or {}).get("Image", "")
        table.add_row(container.labels.get("com.docker.compose.service", container.name),
                      f"[{colour}]{status}[/]", health, image, ports)
    if not table.row_count:
        print("nothing of the project runs")
        return 0
    _print(table)
    return 0


def cmd_drives(argv: list[str]) -> int:
    """Every volume: its folder, whether it exists, its size, who uses it, what the engine has."""
    model = config()
    used = drive_volumes(model["services"])
    client = engine()
    engine_side = project_volumes(client) if client else {}
    table = _table("volume", "folder", "size", "services", "engine")
    problems = 0
    for name in sorted(model["volumes"]):
        path = drive_path(model["volumes"][name])
        if path is None:
            table.add_row(name, "[red]not a dockdrive[/]", "", ", ".join(used.get(name, [])), "")
            problems += 1
            continue
        if path.exists():
            size = folder_size(path)
            size_text = "[yellow]no access[/]" if size is None else f"{size / 2**20:,.1f} MiB"
            folder = f"[green]{path.name}[/]"
        else:
            size_text, folder = "-", f"[grey58]{path.name} (created on up)[/]"
        attrs = engine_side.get(name)
        if attrs is None:
            on_engine = "-"
        elif (attrs.get("Options") or {}).get("device") == str(path):
            on_engine = "[green]ok[/]"
        else:  # created earlier with another path: `docker volume rm` it, the data stays in its folder
            on_engine = f"[red]other path: {(attrs.get('Options') or {}).get('device', '?')}[/]"
            problems += 1
        table.add_row(name, folder, size_text, ", ".join(used.get(name, [])), on_engine)
    _print(table)
    print(f"-- {len(model['volumes'])} volumes in {DOCKDRIVES.relative_to(ROOT)}/", file=sys.stderr)
    return 1 if problems else 0


GROUPS = ["databases", "internals", "automations", "networking", "runners"]
VARIABLE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)(?::-((?:[^{}]|\{[^{}]*\})*))?\}")
SHARED = {
    "REPO_DIR": ("", "repository root: volumes bind ${REPO_DIR}/datasets/_dockdrives/<volume> (tasks set it)"),
    "DOMAIN": ("gr.rs-tech.online", "main domain: routes <name>.DOMAIN, the wildcard certificate, the LDAP base"),
    "BIND": ("127.0.0.1", "interface of the few published ports (traefik); 0.0.0.0 opens them to the network"),
    "TZ": ("Etc/UTC", ""),
}


def cmd_env(argv: list[str]) -> int:
    """Write services/.env.example: every ${VAR:-default} of the service files, by file."""
    out = ["# Settings of services/ - copy the lines you change into .env (git-ignored; the tasks",
           "# also read the forge .env). Generated by `task services:env` from the compose files,",
           "# defaults shown. Change every password before exposing anything.", "", "# shared"]
    seen = set(SHARED)
    for name, (default, note) in SHARED.items():
        out += [f"# {note}"] if note else []
        out.append(f"{name}={default}")
    for group_name in GROUPS:
        for path in sorted((ROOT / "services" / group_name).glob("*.compose.yaml")):
            lines = []
            for match in VARIABLE.finditer(path.read_text(encoding="utf-8")):
                name = match.group(1)
                if name not in seen:
                    seen.add(name)
                    default = re.sub(r"\$\{[A-Z_]+:-([^}]*)\}", r"\1", match.group(2) or "")
                    lines.append(f"{name}={default}")
            if lines:
                out += ["", f"# {group_name}/{path.name.removesuffix('.compose.yaml')}", *lines]
    target = ROOT / "services" / ".env.example"
    target.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{target.relative_to(ROOT)}: {len(seen)} settings")
    return 0


BACKUPS = ROOT / "datasets" / "_backups"


def cmd_backup(argv: list[str]) -> int:
    """Archive dockdrives (all, or the named volumes) into datasets/_backups/, owned by you.

    Containers write their folders as their own users (postgres: uid 70, mode 700), so the
    archive is made inside a throwaway container that can read them all. Services using the
    volumes should be stopped for a consistent copy; --live skips that check.
    """
    live = "--live" in argv
    wanted = [a for a in argv if not a.startswith("-")]
    present = sorted(p.name for p in DOCKDRIVES.iterdir() if p.is_dir()) if DOCKDRIVES.is_dir() else []
    volumes = [v for v in present if not wanted or v in wanted]
    if missing := sorted(set(wanted) - set(present)):
        sys.exit(f"no such dockdrive: {', '.join(missing)} (see: drives)")
    if not volumes:
        sys.exit("nothing to back up: datasets/_dockdrives/ is empty")
    client = engine()
    if client is None:
        sys.exit("no docker or podman engine answers")
    running = set()
    for container in project_containers(client):
        if container.status == "running":
            mounted = {m.get("Name", "") for m in container.attrs.get("Mounts", [])}
            if any(name.endswith(f"_{v}") for v in volumes for name in mounted):
                running.add(container.labels.get("com.docker.compose.service", container.name))
    if running and not live:
        sys.exit(f"still running: {', '.join(sorted(running))} - stop them (task services:down) or pass --live")
    from datetime import datetime, timezone

    BACKUPS.mkdir(parents=True, exist_ok=True)
    label = "all" if not wanted else "-".join(volumes) if len(volumes) <= 3 else f"{len(volumes)}-volumes"
    archive = f"dockdrives-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{label}.tar.gz"
    script = f"tar -czf /out/{archive} -C /drives {' '.join(volumes)} && chown {os.getuid()}:{os.getgid()} /out/{archive}"
    client.containers.run("alpine:3", ["sh", "-c", script], remove=True, volumes={
        str(DOCKDRIVES): {"bind": "/drives", "mode": "ro"},
        str(BACKUPS): {"bind": "/out", "mode": "rw"},
    })
    size = (BACKUPS / archive).stat().st_size
    print(f"{BACKUPS.relative_to(ROOT)}/{archive}  ({size / 2**20:,.1f} MiB, {len(volumes)} volumes)")
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
        case "ps":
            return cmd_ps(rest)
        case "drives":
            return cmd_drives(rest)
        case "backup":
            return cmd_backup(rest)
        case "env":
            return cmd_env(rest)
        case "down":
            return compose("--profile", "*", "down", *rest).returncode
        case "logs":
            return compose("--profile", "*", "logs", "--tail", "100", "-f", *rest).returncode
        case "pull":
            services = config()["services"]
            names = resolve(rest, services) if rest else list(services)
            return compose(*profile_args(names, services), "pull", "--ignore-buildable", *names).returncode
    sys.exit(f"unknown command {command!r}\n{__doc__}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
