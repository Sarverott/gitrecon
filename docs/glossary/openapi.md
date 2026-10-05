# OpenAPI document

> Everything gitrecon can be asked to do, as one generated OpenAPI file.

## What it is

`resources/openapi/gitrecon.openapi.yaml` lists every operation with its fields:

- `POST /commands/<name>` - a gitrecon command; the fields are its arguments, plus `output`
  (`text`, `json`, `urls`);
- `POST /tasks/<name>` - a task of the Taskfile; `args` is what follows `--`.

Each operation has an `operationId` (`command_stars`, `task_openapi`), a tag (the area it
belongs to) and `x-cli`, the same thing as typed in a terminal. Tasks that need a terminal
carry `x-interactive: true`.

It is generated from the command-line parser and from `task --list-all` - nothing in it is
written by hand, so it cannot disagree with the code. It is a **contract**: a GUI can be
built against it, but nothing serves it over HTTP yet.

## Where

`gitrecon.openapi` (`build`); `gitrecon openapi [--format yaml|json]`; `task openapi`
regenerates the file. A test fails when a command changed and the file was not regenerated.

## Relations

Reads the same descriptions the [[menu]] is built from; the data shapes behind `output:
json` are in the integration guide ([[output-mode]]).
