"""Tasks of the project's Taskfiles, with what each one needs as input.

``task --list-all --json`` gives every task (includes resolved, internal ones hidden)
with its description and the file and line it is defined at. pyyaml then reads that
definition: ``{{.CLI_ARGS}}`` means the task takes arguments after ``--``,
``requires.vars`` names variables it cannot run without, ``interactive`` that it
talks to the terminal itself.
"""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

# "e.g. `task recon -- stars sarverott`" -> "stars sarverott"
EXAMPLE_ARGS = re.compile(r"e\.g\.\s*`?task\s+\S+\s+--\s+([^`']+)")
EXAMPLE_VARS = re.compile(r"e\.g\.\s*`?task\s+\S+\s+((?:[A-Z_]+=\S+\s*)+)")


@dataclass
class TaskInfo:
    name: str
    desc: str = ""
    file: Path | None = None
    line: int | None = None
    takes_args: bool = False
    required_vars: list[str] = field(default_factory=list)
    interactive: bool = False
    example_args: str = ""
    example_vars: dict[str, str] = field(default_factory=dict)

    @property
    def namespace(self) -> str:
        """Section of the menu: the include it comes from, or ``project`` for the root."""
        return self.name.split(":", 1)[0] if ":" in self.name else "project"

    def command(self, args: str = "", variables: dict[str, str] | None = None) -> list[str]:
        cmd = ["task", self.name, *(f"{k}={v}" for k, v in (variables or {}).items())]
        if args.strip():
            cmd += ["--", *shlex.split(args)]  # keeps -m "a message" together
        return cmd


@cache
def _load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def definition(full_name: str, path: Path) -> dict[str, Any]:
    """A task's YAML definition, found in its file by the longest key its full name ends with."""
    tasks = (_load(path).get("tasks") or {}) if path.exists() else {}
    candidates = [k for k in tasks if full_name == k or full_name.endswith(":" + k)]
    if not candidates:
        return {}
    value = tasks[max(candidates, key=len)]
    return value if isinstance(value, dict) else {"cmds": value}


def describe(entry: dict[str, Any]) -> TaskInfo:
    """``task --list-all --json`` entry -> TaskInfo (with its YAML definition read)."""
    location = entry.get("location") or {}
    path = Path(location["taskfile"]) if location.get("taskfile") else None
    spec = definition(entry["name"], path) if path else {}
    desc = entry.get("desc") or spec.get("desc") or ""
    example_vars = {}
    if (m := EXAMPLE_VARS.search(desc)):
        example_vars = dict(pair.split("=", 1) for pair in m.group(1).split())
    m = EXAMPLE_ARGS.search(desc)
    return TaskInfo(
        name=entry["name"],
        desc=desc,
        file=path,
        line=location.get("line"),
        takes_args="CLI_ARGS" in yaml.safe_dump(spec),
        required_vars=list((spec.get("requires") or {}).get("vars") or []),
        interactive=bool(spec.get("interactive")),
        example_args=re.sub(r"\s*\(.*\)\s*$", "", m.group(1)).strip() if m else "",  # drop "(default: ...)"
        example_vars=example_vars,
    )


def available() -> bool:
    return shutil.which("task") is not None


def discover(root: Path) -> list[TaskInfo]:
    """Every listed task of the Taskfile in ``root`` (empty without Task or a Taskfile)."""
    if not available() or not any((root / name).exists() for name in ("Taskfile.yml", "Taskfile.yaml")):
        return []
    result = subprocess.run(["task", "--list-all", "--json"], cwd=root, capture_output=True, text=True,
                            check=False)
    if result.returncode != 0:
        return []
    return [describe(entry) for entry in json.loads(result.stdout).get("tasks", []) if entry["name"] != "default"]
