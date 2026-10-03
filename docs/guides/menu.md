# The interactive menu

```sh
task menu          # or: uv run gitrecon    (plain `gitrecon` in a terminal opens it)
                   # or: uv run gitrecon menu, task docker:run -- menu
```

A full-screen [[menu]] for everything gitrecon can do, so you don't need to remember a
command, a flag or a task name.

| Section | What it does |
| --- | --- |
| Run a gitrecon command | pick a command, answer its form, pick the [[output-mode]], confirm the command line, run |
| Run a task | every task of the Taskfiles, grouped by include (`docs`, `examples`, `gh`, ...) |
| Examples | an example's README; `l` launches Jupyter, `r` runs it headless, `m` converts to marimo |
| Manuals | these docs rendered as markdown; `l` follows `[[links]]`, `b` goes back |
| Status | credentials, tools, raw buffer, link catalog and the local map copy |

## Keys

| Key | In lists | In viewers |
| --- | --- | --- |
| ↑ ↓, PgUp PgDn, Home End | move | scroll |
| typing | filters (every word must match name, description or section) | - |
| Enter | choose | back |
| Space | marks an option (option lists) | page down |
| Esc | clears the filter, then goes back | back |
| q | (types into the filter) | back |
| Ctrl+C | leaves the menu; while a command runs, stops the command | |

## Forms

A command's form is read from the CLI itself, so new commands and options appear on their
own. Positional arguments are asked first (with their defaults); then an option list
lets you mark which options to set - only those are asked. Choices open as lists, flags as
yes/no, numbers and lists as typed values. Before anything runs you see the exact command
line, e.g. `gitrecon rfc --search quic --urls`.

- **text** runs straight in the terminal.
- **json** shows the result highlighted and scrollable, notes above it.
- **urls** shows the addresses as a numbered list of clickable links (in terminals that
  support links).
- `events --watch` always runs in the terminal; Ctrl+C stops it and returns to the menu.

Tasks that take arguments (`{{.CLI_ARGS}}`) ask for them, with the example from the task's
description as the default; tasks with `requires: vars` ask for those variables.

Last answers are remembered per command and task in `data/state/menu.json`, so a repeated
run is a few presses of Enter.

## In a container

The image has no Task, examples or docs, so the menu there offers the commands and the
status board.
