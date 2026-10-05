"""The generated OpenAPI document: built from the parser and the Taskfile, and kept in step."""

from pathlib import Path

import yaml

from gitrecon.main import main
from gitrecon.openapi import build
from gitrecon.tui import commands

SAVED = Path(__file__).resolve().parents[1] / "resources" / "openapi" / "gitrecon.openapi.yaml"


def test_every_command_is_an_operation_with_its_arguments():
    document = build()
    assert document["openapi"] == "3.1.0" and document["info"]["title"] == "gitrecon"
    specs = commands.discover()
    assert {f"/commands/{s.name}" for s in specs} == {p for p in document["paths"] if p.startswith("/commands/")}
    stars = document["paths"]["/commands/stars"]["post"]
    body = stars["requestBody"]["content"]["application/json"]["schema"]
    assert stars["operationId"] == "command_stars" and stars["tags"] == ["collect"] and stars["x-cli"] == "gitrecon stars <user>"
    assert body["required"] == ["user"] and body["properties"]["save"] == {
        "type": "boolean", "description": "also store them in the raw buffer"}
    assert body["properties"]["output"]["enum"] == ["text", "json", "urls"]
    score = document["paths"]["/commands/score"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert score["properties"]["format"]["enum"] == ["tab", "abc", "midi"] and score["properties"]["max_commits"]["type"] == "integer"
    ids = [op["post"]["operationId"] for op in document["paths"].values()]
    assert len(ids) == len(set(ids))                                        # a GUI can key on them


def test_the_saved_document_matches_the_commands(capsys):
    """`task openapi` was run after the last change of a command (tasks are checked where Task exists)."""
    saved = yaml.safe_load(SAVED.read_text(encoding="utf-8"))
    current = build()
    only_commands = lambda doc: {p: v for p, v in doc["paths"].items() if p.startswith("/commands/")}  # noqa: E731
    assert only_commands(saved) == only_commands(current), "run: task openapi"
    assert main(["openapi", "--format", "json"]) == 0
    assert '"openapi": "3.1.0"' in capsys.readouterr().out
