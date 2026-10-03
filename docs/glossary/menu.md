# Menu

> The full-screen, arrow-driven way to run gitrecon: commands, tasks, examples, manuals, status.

## What it is

Lists drawn with rich: the cursor moves with the arrows, typing filters, Enter chooses,
Esc goes back. Commands are read from the CLI parser and become forms; tasks are read
from `task --list-all --json` and their YAML (arguments, required variables); documents
render as markdown; `--json` and `--urls` results open in a scrolling, coloured viewer.

## Where

`gitrecon.tui`: `app` (the menu), `widgets` (`Selector`, `Viewer`, prompts), `commands`
(CLI → forms → argv), `taskfiles`, `manuals`, `keys`, `theme`. CLI: `gitrecon menu`, or
plain `gitrecon` in a terminal; `task menu`. Guide: the interactive menu (`guides/menu.md`).

## Relations

Offers every command with its [[output-mode]]; reads the [[documentation]] pages; runs the
tasks of the [[craft-loop]] and the [[examples]].
