"""gitrecon's interface as one OpenAPI document - generated, never written by hand.

    gitrecon openapi > resources/openapi/gitrecon.openapi.yaml      (task openapi)

Two kinds of operation, both read from what already defines them:

- ``POST /commands/<name>`` - a gitrecon command; its fields are the command's arguments
  (from ``gitrecon.cli.build_parser()``).
- ``POST /tasks/<name>`` - a task of the Taskfile (from ``task --list-all``).

It is a contract: what can be asked and with which fields. Nothing serves it over HTTP yet.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gitrecon.config import PROJECT_ROOT
from gitrecon.tui import commands, taskfiles

SECTIONS = {"collect": "collect - bring data in", "analyze": "analyze - read and draw what was collected",
            "atlas": "atlas - the map dataset", "content": "content - text, commits, digests"}


def _field(option: commands.Option) -> dict[str, Any]:
    kinds = {"flag": {"type": "boolean"}, "int": {"type": "integer"},
             "list": {"type": "array", "items": {"type": "string"}}}
    schema: dict[str, Any] = dict(kinds.get(option.kind, {"type": "string"}))
    if option.choices:
        schema["enum"] = list(option.choices)
    if option.help:
        schema["description"] = option.help
    if option.default not in (None, "", [], False):
        schema["default"] = option.default
    return schema


def _command(spec: commands.CommandSpec) -> dict[str, Any]:
    fields = {option.dest: _field(option) for option in spec.options}
    fields["output"] = {"type": "string", "enum": spec.modes, "default": "text",
                        "description": "text for people; json / urls: data only"}
    body: dict[str, Any] = {"type": "object", "properties": fields, "additionalProperties": False}
    if required := [o.dest for o in spec.options if o.required]:
        body["required"] = required
    usage = " ".join(["gitrecon", spec.name, *(f"<{o.dest}>" if o.required else f"[{o.dest}]" for o in spec.positionals)])
    return {"post": {
        "operationId": "command_" + spec.name.replace("-", "_"),
        "tags": [spec.section],
        "summary": spec.help,
        "x-cli": usage,
        "requestBody": {"content": {"application/json": {"schema": body}}},
        "responses": {"200": {"description": "the command's output", "content": {
            "application/json": {"schema": {}}, "text/plain": {"schema": {"type": "string"}}}},
            "400": {"description": "the command refused the arguments or failed"}},
    }}


def _task(task: taskfiles.TaskInfo) -> dict[str, Any]:
    fields: dict[str, Any] = {name: {"type": "string"} for name in task.required_vars}
    if task.takes_args:
        fields["args"] = {"type": "string", "description": "what follows `--` on the command line"}
        if task.example_args:
            fields["args"]["examples"] = [task.example_args]
    operation: dict[str, Any] = {
        "operationId": "task_" + task.name.replace(":", "_").replace("-", "_"),
        "tags": ["task: " + task.namespace],
        "summary": task.desc,
        "x-cli": "task " + task.name + (" -- <args>" if task.takes_args else ""),
        "responses": {"200": {"description": "the task's output", "content": {"text/plain": {"schema": {"type": "string"}}}}},
    }
    if fields:
        body: dict[str, Any] = {"type": "object", "properties": fields, "additionalProperties": False}
        if task.required_vars:
            body["required"] = list(task.required_vars)
        operation["requestBody"] = {"content": {"application/json": {"schema": body}}}
    if task.interactive:
        operation["x-interactive"] = True  # needs a terminal: not for a GUI to call blindly
    return {"post": operation}


def build(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """The OpenAPI 3.1 document: every command, and every task Task can list in ``root``."""
    meta = json.loads((root / "metadata.json").read_text(encoding="utf-8")) if (root / "metadata.json").exists() else {}
    specs = commands.discover()
    tasks = taskfiles.discover(root)
    paths = {f"/commands/{spec.name}": _command(spec) for spec in specs}
    paths |= {f"/tasks/{task.name}": _task(task) for task in tasks}
    tags = [{"name": name, "description": SECTIONS.get(name, name)} for name in dict.fromkeys(s.section for s in specs)]
    tags += [{"name": name} for name in dict.fromkeys("task: " + t.namespace for t in tasks)]
    return {
        "openapi": "3.1.0",
        "info": {"title": meta.get("name", "gitrecon"), "version": meta.get("version", "0"),
                 "description": (meta.get("description", "") + "\n\nGenerated from the command-line parser and the "
                                 "Taskfile (`task openapi`); do not edit. A contract: no server answers it yet.").strip()},
        "tags": tags,
        "paths": paths,
    }
