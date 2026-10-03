"""services/: the compose layout's conventions, and control.py's dependency resolution."""

import importlib.util
import re
import shutil
import subprocess

import pytest
import yaml

from gitrecon.config import PROJECT_ROOT

SERVICES = PROJECT_ROOT / "services"
GROUPS = ["databases", "internals", "automations", "networking", "runners"]

spec = importlib.util.spec_from_file_location("services_control", SERVICES / "control.py")
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


def service_files(group: str):
    return sorted((SERVICES / group).glob("*.compose.yaml"))


def includes(path):
    return [entry if isinstance(entry, str) else entry["path"] for entry in yaml.safe_load(path.read_text())["include"]]


# --- layout ----------------------------------------------------------------------


def test_root_and_index_include_every_group():
    assert "services/compose.yaml" in includes(PROJECT_ROOT / "compose.yaml")
    assert includes(SERVICES / "compose.yaml") == [f"./{g}/compose.yaml" for g in GROUPS]


@pytest.mark.parametrize("group", GROUPS)
def test_group_includes_each_service_file(group):
    assert sorted(includes(SERVICES / group / "compose.yaml")) == [f"./{f.name}" for f in service_files(group)]


@pytest.mark.parametrize("group", GROUPS)
def test_services_follow_conventions(group):
    note = (SERVICES / group / "NOTE.md").read_text()
    for path in service_files(group):
        text = path.read_text()
        assert not re.search(r"\$\{[A-Z_]+:\?", text), f"{path.name}: ${{VAR:?}} breaks every compose command"
        for name, svc in yaml.safe_load(text)["services"].items():
            profiles = svc.get("profiles")
            assert profiles and profiles[0] == group, f"{name}: first profile must be the group"
            assert name in profiles or profiles[1] in yaml.safe_load(text)["services"], f"{name}: own profile"
            for port in svc.get("ports", []):
                host = port.split(":")[0]
                # through ${BIND} (or a *_BIND), or pinned to localhost (traefik's open dashboard)
                assert "BIND" in host or host == "127.0.0.1", f"{name}: publish {port!r} through ${{BIND}}"
        assert path.name.removesuffix(".compose.yaml") in note, f"{path.name} missing from {group}/NOTE.md"


def test_env_example_covers_every_variable():
    documented = set(re.findall(r"^([A-Z_][A-Z0-9_]*)=", (SERVICES / ".env.example").read_text(), re.M))
    used = set()
    for group in GROUPS:
        for path in service_files(group):
            used |= set(re.findall(r"\$\{([A-Z_][A-Z0-9_]*)", path.read_text()))
    assert used <= documented, f"not in services/.env.example: {sorted(used - documented)}"


@pytest.mark.skipif(not shutil.which("docker"), reason="docker is not installed")
def test_compose_model_is_valid():
    for profiles in ([], ["--profile", "*"]):
        done = subprocess.run(["docker", "compose", *profiles, "config", "-q"], cwd=PROJECT_ROOT,
                              capture_output=True, text=True, check=False)
        assert done.returncode == 0, done.stderr


# --- control.py ------------------------------------------------------------------

MODEL = {
    "postgres": {"profiles": ["databases", "postgres"]},
    "redis": {"profiles": ["databases", "redis"]},
    "gitea": {"profiles": ["internals", "gitea"], "depends_on": {"postgres": {}}},
    "n8n": {"profiles": ["automations", "n8n"], "depends_on": {"postgres": {}}},
    "gitea-runner": {"profiles": ["runners", "gitea-runner"], "depends_on": {"gitea": {}}},
    "gitrecon": {},
}


def test_resolve_follows_dependencies_across_groups():
    assert control.resolve(["gitea-runner"], MODEL) == ["gitea-runner", "gitea", "postgres"]
    assert control.resolve(["internals", "n8n"], MODEL) == ["gitea", "n8n", "postgres"]
    assert control.resolve(["databases"], MODEL) == ["postgres", "redis"]


def test_resolve_rejects_unknown_targets():
    with pytest.raises(SystemExit):
        control.resolve(["nope"], MODEL)


def test_profile_args_enable_only_needed_services():
    assert control.profile_args(["gitea", "postgres"], MODEL) == ["--profile", "gitea", "--profile", "postgres"]
    assert control.group(MODEL["gitrecon"]) == "gitrecon"
