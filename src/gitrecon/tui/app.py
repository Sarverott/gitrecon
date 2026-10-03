"""The interactive menu: ``gitrecon menu`` (or plain ``gitrecon`` in a terminal, or ``task menu``).

Main menu → gitrecon commands (forms built from the CLI parser), Taskfile tasks,
examples, manuals and a status board. Lists are full-screen and driven by the arrows;
answers are asked with rich prompts; results of ``--json`` and ``--urls`` runs open in
a scrolling, coloured viewer. Last answers are remembered in ``data/state/menu.json``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Group
from rich.json import JSON
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from gitrecon.config import PROJECT_ROOT, Config, env_files
from gitrecon.tui import commands as cli_commands
from gitrecon.tui import manuals, taskfiles
from gitrecon.tui.commands import CommandSpec, Option
from gitrecon.tui.theme import LOGO, console
from gitrecon.tui.widgets import Item, Selector, Viewer, ask_int, ask_text, ask_yes, choose, wait_key

HIGHLIGHT_LIMIT = 400_000  # characters of JSON still worth colouring

MODE_ITEMS = {
    "text": ("text", "text", "readable output, straight in the terminal"),
    "json": ("json", "json", "data for programs - shown here highlighted and scrollable"),
    "urls": ("urls", "urls", "web addresses only - shown here as clickable links"),
}
SECTION_NAMES = {"collect": "collect", "analyze": "look & conclude", "atlas": "map dataset", "content": "content & text"}


@dataclass
class Memory:
    """Last answers per command and task, so a repeated run is a couple of enters."""

    path: Path
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}

    def get(self, kind: str, name: str) -> dict[str, Any]:
        return dict(self.data.get(kind, {}).get(name, {}))

    def put(self, kind: str, name: str, value: dict[str, Any]) -> None:
        self.data.setdefault(kind, {})[name] = value
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, indent=1, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass  # a read-only data dir must not break the menu


class MenuApp:
    def __init__(self, config: Config | None = None, root: Path = PROJECT_ROOT):
        self.config = config or Config()
        self.root = root
        self.out = console()
        self.memory = Memory(self.config.state_dir / "menu.json")
        self.commands = cli_commands.discover()
        self.tasks = taskfiles.discover(root)
        self.examples = sorted(p.parent for p in (root / "examples").glob("*/Taskfile.yml"))

    # --- main loop --------------------------------------------------------------

    def main_items(self) -> list[Item]:
        items = [Item("Run a gitrecon command", self.pick_command, f"{len(self.commands)} commands, with forms")]
        if self.tasks:
            items.append(Item("Run a task", self.pick_task, f"{len(self.tasks)} tasks from the Taskfiles"))
        if self.examples:
            items.append(Item("Examples", self.pick_example, f"{len(self.examples)} notebook examples"))
        if manuals.pages():
            items.append(Item("Manuals", self.pick_manual, "guides and glossary from docs/"))
        items += [Item("Status", self.show_status, "data, map, credentials, tools"),
                  Item("Quit", None, "or esc")]
        return items

    def headline(self) -> str:
        token = "[ok]✓ GitHub token[/ok]" if self.config.github_token else "[warn]✗ no GitHub token (60 req/h)[/warn]"
        raw = self.config.raw_dir
        sources = sorted(p.name for p in raw.iterdir() if p.is_dir()) if raw.is_dir() else []
        return f"{token} · [muted]raw buffer:[/muted] {', '.join(sources) or 'empty'}"

    def run(self) -> int:
        try:
            while True:
                action = Selector("menu", self.main_items(), subtitle=self.headline()).run(self.out)
                if action is None:
                    return 0
                action()
        except KeyboardInterrupt:
            self.out.print("\n[muted]bye[/muted]")
            return 130

    # --- gitrecon commands ------------------------------------------------------------

    def pick_command(self) -> None:
        items = [Item(spec.name, spec, spec.help, SECTION_NAMES.get(spec.section, spec.section))
                 for spec in self.commands]
        spec = Selector("gitrecon commands", items).run(self.out)
        if spec:
            self.run_command(spec)

    def ask(self, option: Option, default: Any) -> Any:
        label = f"{option.label}" + (f" [muted]({option.help})[/muted]" if option.help else "")
        if option.kind == "choice":
            return choose(option.label, option.choices, subtitle=option.help) or default
        if option.kind == "flag":
            return ask_yes(label, default=bool(default))
        if option.kind == "int":
            return ask_int(label, default=default if isinstance(default, int) else None)
        if option.kind == "list":
            value = default if isinstance(default, str) else " ".join(default or [])
            return ask_text(f"{label} [muted](space separated)[/muted]", default=value or None,
                            required=option.required)
        return ask_text(label, default=str(default) if default not in (None, "") else None, required=option.required)

    def run_command(self, spec: CommandSpec) -> None:
        remembered = self.memory.get("commands", spec.name)
        answers: dict[str, Any] = dict(remembered.get("answers", {}))
        self.out.clear()
        self.out.print(Panel(f"[accent]gitrecon {spec.name}[/accent]\n[muted]{spec.help}[/muted]",
                             title=LOGO, border_style="red"))
        for option in spec.positionals:
            answers[option.dest] = self.ask(option, answers.get(option.dest, option.default))

        if spec.optionals:
            items = [Item(o.label, o, o.help) for o in spec.optionals]
            picker = Selector(f"{spec.name} · options to set", items, multi=True,
                              subtitle="[muted]space marks an option, enter continues (nothing marked: defaults)[/muted]")
            picker.marked = {i for i, o in enumerate(spec.optionals)
                             if answers.get(o.dest) not in (None, "", False, [], o.default)}
            chosen = picker.run(self.out)
            if chosen is None:
                return
            for option in spec.optionals:
                if option not in chosen:
                    answers[option.dest] = option.default if option.kind != "flag" else False
                elif option.kind == "flag":
                    answers[option.dest] = True
                else:
                    answers[option.dest] = self.ask(option, answers.get(option.dest) or option.default)

        mode = "text"
        if len(spec.modes) > 1:
            last = remembered.get("mode", "text")
            options = [MODE_ITEMS[m] for m in spec.modes]
            options.sort(key=lambda o: o[1] != last)  # last used first
            mode = choose(f"{spec.name} · output", options) or "text"

        line = spec.line(answers, mode)
        self.out.print(Text.assemble(("\n  ", ""), (f" {line} ", "cmd"), ("\n", "")))
        if not ask_yes("run it?", default=True):
            return
        self.memory.put("commands", spec.name, {"answers": answers, "mode": mode})
        self.execute(spec.argv(answers, mode), line, mode, attached=bool(answers.get("watch")))

    def execute(self, argv: list[str], line: str, mode: str, attached: bool = False) -> None:
        cmd = [sys.executable, "-m", "gitrecon", *argv]
        if mode == "text" or attached:  # streams (events --watch) stay attached to the terminal
            self.attached(cmd, line)
            return
        with self.out.status(f"[accent]{line}[/accent]", spinner="dots"):
            try:
                done = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, check=False)
            except KeyboardInterrupt:
                return
        notes = Text(done.stderr.strip(), style="muted") if done.stderr.strip() else Text("")
        if done.returncode != 0:
            Viewer(f"{line} · exit {done.returncode}", Group(Text(done.stdout), notes)).run(self.out)
            return
        body = self.render_json(done.stdout) if mode == "json" else self.render_urls(done.stdout)
        Viewer(line, Group(notes, body) if notes.plain else body).run(self.out)

    @staticmethod
    def render_json(text: str):
        if len(text) > HIGHLIGHT_LIMIT:
            return Text(text)
        try:
            return JSON(text)
        except ValueError:  # JSON Lines (events) or anything else
            return Text(text)

    @staticmethod
    def render_urls(text: str) -> Table:
        urls = [line for line in text.splitlines() if line.strip()]
        table = Table(box=None, show_header=False, padding=(0, 1))
        table.add_column(style="muted", justify="right")
        table.add_column()
        for i, url in enumerate(urls, start=1):
            table.add_row(str(i), Text(url, style=f"url link {url}"))
        return table

    # --- tasks ------------------------------------------------------------------------

    def pick_task(self) -> None:
        items = []
        for task in self.tasks:
            needs = " · needs input" if task.takes_args or task.required_vars else ""
            items.append(Item(task.name, task, f"{task.desc}{needs}", task.namespace))
        task = Selector("tasks", items).run(self.out)
        if task:
            self.run_task(task)

    def run_task(self, task: taskfiles.TaskInfo) -> None:
        remembered = self.memory.get("tasks", task.name)
        self.out.clear()
        where = f"{task.file.relative_to(self.root)}:{task.line}" if task.file else ""
        self.out.print(Panel(f"[accent]task {task.name}[/accent]\n{task.desc}\n[muted]{where}[/muted]",
                             title=LOGO, border_style="red"))
        variables = {}
        for var in task.required_vars:
            default = remembered.get("vars", {}).get(var) or task.example_vars.get(var)
            variables[var] = ask_text(var, default=default, required=True)
        args = ""
        if task.takes_args:
            args = ask_text("arguments after --", default=remembered.get("args") or task.example_args or None)
        cmd = task.command(args, variables)
        self.out.print(Text.assemble(("\n  ", ""), (f" {' '.join(cmd)} ", "cmd"), ("\n", "")))
        if not ask_yes("run it?", default=True):
            return
        self.memory.put("tasks", task.name, {"args": args, "vars": variables})
        self.attached(cmd, " ".join(cmd))

    def attached(self, cmd: list[str], line: str, cwd: Path | None = None) -> None:
        self.out.print(Rule(line, style="red"))
        try:
            code = subprocess.run(cmd, cwd=cwd or self.root, check=False).returncode
        except KeyboardInterrupt:
            code = 130
        self.out.print(Rule(f"exit {code}", style="ok" if code == 0 else "fail"))
        wait_key()

    # --- examples ---------------------------------------------------------------------

    def pick_example(self) -> None:
        items = []
        for folder in self.examples:
            notebooks = ", ".join(p.name for p in sorted(folder.glob("*.ipynb")))
            items.append(Item(folder.name, folder, notebooks))
        folder = Selector("examples", items).run(self.out)
        if not folder:
            return
        readme = folder / "README.md"
        body = Markdown(readme.read_text(encoding="utf-8")) if readme.exists() else Text(folder.name)
        actions = {"l": "launch jupyter", "r": "run headless", "m": "convert to marimo"}
        key = Viewer(f"examples/{folder.name}", body, extra_keys=actions).run(self.out)
        task_name = {"l": "launch", "r": "run", "m": "marimo"}.get(key or "")
        if task_name and taskfiles.available():
            self.attached(["task", task_name], f"task {task_name} (examples/{folder.name})", cwd=folder)

    # --- manuals ----------------------------------------------------------------------

    def pick_manual(self) -> None:
        items = [Item(manuals.title(p), p, manuals.name(p), manuals.section(p)) for p in manuals.pages()]
        page = Selector("manuals", items).run(self.out)
        history: list[Path] = []
        while page:
            targets = manuals.links(page)
            extra = {"l": f"links ({len(targets)})"} if targets else {}
            if history:
                extra["b"] = "previous page"
            key = Viewer(f"docs/{manuals.name(page)}.md", manuals.markdown(page), extra_keys=extra).run(self.out)
            if key == "b":
                page = history.pop()
            elif key == "l":
                target = choose("linked pages", targets)
                found = manuals.find(target) if target else []
                if found:
                    history.append(page)
                    page = found[0]
            else:
                page = None

    # --- status -----------------------------------------------------------------------

    def status_board(self) -> Group:
        from gitrecon.storage import RawBuffer

        def mark(ok: bool) -> str:
            return "[ok]✓[/ok]" if ok else "[fail]✗[/fail]"

        setup = Table.grid(padding=(0, 2))
        setup.add_row("data", str(self.config.data_dir))
        setup.add_row("map copy", str(self.config.datasets_dir / "imperialmap"))
        setup.add_row("GitHub token", mark(bool(self.config.github_token)))
        setup.add_row("HF token", mark(bool(os.environ.get("HF_TOKEN"))))
        setup.add_row("env files", ", ".join(str(p) for p in env_files() if p.is_file()) or "-")
        tools = {name: shutil.which(name) for name in ("task", "docker", "gh", "uv", "ollama")}
        setup.add_row("tools", "  ".join(f"{mark(bool(path))} {name}" for name, path in tools.items()))

        buffer = RawBuffer(self.config.raw_dir)
        raw = Table("source", "files", "MiB", "latest", box=None, header_style="section")
        for source in buffer.sources():
            files = buffer.files(source)
            size = sum(f.stat().st_size for f in files) / 2**20
            raw.add_row(source, str(len(files)), f"{size:,.1f}", files[-1].parent.name if files else "-")

        parts = [Panel(setup, title="[section]setup[/section]", border_style="grey37"),
                 Panel(raw if buffer.sources() else Text("empty", style="muted"),
                       title="[section]raw buffer[/section]", border_style="grey37")]

        if self.config.links_catalog.exists():
            from gitrecon.sources.links import load_catalog

            kinds = Counter(link.kind for link in load_catalog(self.config.links_catalog))
            parts.append(Panel(Text(", ".join(f"{k} {n}" for k, n in kinds.most_common())),
                               title="[section]link catalog[/section]", border_style="grey37"))

        drives = self.root / "datasets" / "_dockdrives"
        if drives.is_dir():
            folders = sorted(p.name for p in drives.iterdir() if p.is_dir())
            parts.append(Panel(Text(", ".join(folders) or "none yet", style="default" if folders else "muted"),
                               title=f"[section]service volumes · datasets/_dockdrives ({len(folders)})[/section]",
                               border_style="grey37"))

        local_map = self.config.datasets_dir / "imperialmap"
        if local_map.is_dir():
            areas = Table("area", "files", box=None, header_style="section")
            for area in sorted(p for p in local_map.iterdir() if p.is_dir() and not p.name.startswith(".")):
                areas.add_row(area.name, str(sum(1 for f in area.rglob("*") if f.is_file())))
            parts.append(Panel(areas, title="[section]map dataset[/section]", border_style="grey37"))
        return Group(*parts)

    def show_status(self) -> None:
        with self.out.status("[accent]looking around…[/accent]"):
            board = self.status_board()
        Viewer("status", board).run(self.out)


def run_menu(config: Config | None = None) -> int:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("the menu needs an interactive terminal (try: gitrecon --help)", file=sys.stderr)
        return 2
    return MenuApp(config).run()
