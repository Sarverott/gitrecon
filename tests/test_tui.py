"""The interactive menu: keys, widgets, Taskfile and command discovery, manuals, the app pieces."""

import shutil
from pathlib import Path

import pytest
from rich.console import Console

from gitrecon.config import PROJECT_ROOT, Config
from gitrecon.main import main
from gitrecon.tui import commands, keys, manuals, taskfiles
from gitrecon.tui.app import MenuApp, Memory
from gitrecon.tui.theme import THEME
from gitrecon.tui.widgets import CANCEL, DONE, Item, Selector, Viewer

def themed(width: int) -> Console:
    return Console(record=True, width=width, theme=THEME)


# --- keys ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "key"),
    [(b"\x1b[A", keys.UP), (b"\x1b[B", keys.DOWN), (b"\x1bOA", keys.UP), (b"\x1b[5~", keys.PAGE_UP),
     (b"\x1b[H", keys.HOME), (b"\r", keys.ENTER), (b"\x1b", keys.ESCAPE), (b"\x7f", keys.BACKSPACE),
     (b" ", keys.SPACE), (b"q", "q"), ("ł".encode(), "ł")],
)
def test_decode(raw, key):
    assert keys.decode(raw) == key


def test_ctrl_c_interrupts():
    with pytest.raises(KeyboardInterrupt):
        keys.decode(b"\x03")


# --- selector and viewer ------------------------------------------------------------


def items():
    return [Item("stars", "s", "list starred repositories", "collect"),
            Item("feeds", "f", "read RSS/Atom feeds", "collect"),
            Item("label", "l", "conclude labels", "look")]


def test_selector_moves_within_bounds_and_chooses():
    sel = Selector("t", items())
    sel.handle(keys.UP)
    assert sel.cursor == 0
    for _ in range(5):
        sel.handle(keys.DOWN)
    assert sel.cursor == 2
    assert sel.handle(keys.ENTER) == DONE and sel.result() == "l"


def test_selector_typing_filters_and_escape_clears_then_cancels():
    sel = Selector("t", items())
    for ch in "rss":
        sel.handle(ch)
    assert [item.value for _, item in sel.visible()] == ["f"]  # matches the hint
    assert sel.handle(keys.ESCAPE) is None and sel.query == ""
    assert sel.handle(keys.ESCAPE) == CANCEL


def test_selector_matches_every_word_and_section():
    sel = Selector("t", items(), query="look conclude")
    assert [item.value for _, item in sel.visible()] == ["l"]


def test_selector_multi_marks_with_space():
    sel = Selector("t", items(), multi=True)
    sel.handle(keys.SPACE)
    sel.handle(keys.DOWN)
    sel.handle(keys.DOWN)
    sel.handle(keys.SPACE)
    assert sel.handle(keys.ENTER) == DONE and sel.result() == ["s", "l"]
    sel.handle(keys.SPACE)  # unmark
    assert sel.result() == ["s"]


def test_selector_renders_sections_and_items():
    out = themed(80)
    out.print(Selector("menu", items(), subtitle="hello").render(20))
    text = out.export_text()
    assert "── collect" in text and "stars" in text and "hello" in text and "3/3" in text


def test_viewer_scrolls_within_bounds_and_returns_extra_keys():
    viewer = Viewer("doc", "x", extra_keys={"l": "links"})
    assert viewer.handle(keys.PAGE_DOWN, height=10, total=100) is None and viewer.offset == 6
    viewer.handle(keys.END, height=10, total=100)
    assert viewer.offset == 94
    viewer.handle(keys.HOME, height=10, total=100)
    assert viewer.offset == 0
    assert viewer.handle("l", 10, 100) == "l"
    assert viewer.handle("q", 10, 100) == CANCEL


# --- Taskfiles ---------------------------------------------------------------------


@pytest.fixture
def taskfile(tmp_path):
    path = tmp_path / "Taskfile.yml"
    path.write_text(
        "version: '3'\n"
        "tasks:\n"
        "  recon:\n"
        "    desc: 'Run the CLI, e.g. `task recon -- stars sarverott`'\n"
        "    cmds: ['uv run gitrecon {{.CLI_ARGS}}']\n"
        "  release:notes:\n"
        "    desc: 'Notes, e.g. task gh:release:notes TAG=v0.1.0'\n"
        "    requires: {vars: [TAG]}\n"
        "    cmds: ['echo {{.TAG}}']\n"
        "  commit:\n"
        "    interactive: true\n"
        "    cmds: ['cz commit']\n"
    )
    return path


def test_describe_reads_inputs_from_yaml(taskfile):
    recon = taskfiles.describe({"name": "recon", "desc": "", "location": {"taskfile": str(taskfile), "line": 3}})
    assert recon.takes_args and recon.example_args == "stars sarverott" and recon.namespace == "project"

    notes = taskfiles.describe({"name": "gh:release:notes", "desc": "Notes, e.g. task gh:release:notes TAG=v0.1.0",
                                "location": {"taskfile": str(taskfile)}})
    assert notes.required_vars == ["TAG"] and notes.example_vars == {"TAG": "v0.1.0"}
    assert notes.namespace == "gh" and not notes.takes_args

    commit = taskfiles.describe({"name": "commit", "location": {"taskfile": str(taskfile)}})
    assert commit.interactive and not commit.takes_args


def test_task_command_keeps_quoted_arguments():
    task = taskfiles.TaskInfo("map:push")
    assert task.command('-m "dnstrees from gists"') == ["task", "map:push", "--", "-m", "dnstrees from gists"]
    assert taskfiles.TaskInfo("gh:release:notes").command(variables={"TAG": "v1"}) == ["task", "gh:release:notes", "TAG=v1"]


@pytest.mark.skipif(not shutil.which("task"), reason="Task is not installed")
def test_discover_project_tasks():
    found = {t.name: t for t in taskfiles.discover(PROJECT_ROOT)}
    assert "default" not in found
    assert found["recon"].takes_args and found["examples:run"].namespace == "examples"
    assert found["gh:release:notes"].required_vars == ["TAG"]


def test_discover_without_taskfile(tmp_path):
    assert taskfiles.discover(tmp_path) == []


# --- gitrecon commands as forms ------------------------------------------------------


@pytest.fixture(scope="module")
def specs():
    return {spec.name: spec for spec in commands.discover()}


def test_every_command_but_the_menu_is_offered(specs):
    assert "menu" not in specs and {"stars", "rfc", "atlas", "label"} <= set(specs)
    assert specs["stars"].modes == ["text", "json", "urls"] and specs["status"].modes == ["text", "json"]
    assert specs["stars"].section == "collect" and specs["label"].section == "analyze"


def test_option_kinds(specs):
    kinds = {o.label: o.kind for o in specs["rfc"].options}
    assert kinds == {"--search": "list", "--number": "list", "--limit": "int", "--save": "flag"}
    action = specs["atlas"].positionals[0]
    assert action.kind == "choice" and "push" in action.choices and action.required


def test_argv_building(specs):
    assert specs["stars"].argv({"user": "sarverott", "save": True}, "urls") == ["stars", "sarverott", "--save", "--urls"]
    assert specs["links"].argv({"root": "..", "kind": "feed gist"}) == ["links", "..", "--kind", "feed", "--kind", "gist"]
    assert specs["rfc"].argv({"search": "quic tls", "limit": 20}) == ["rfc", "--search", "quic", "tls"]
    assert specs["atlas"].line({"action": "push", "message": "a b"}) == "gitrecon atlas push --message 'a b'"


# --- manuals ------------------------------------------------------------------------


def test_manuals_pages_and_links():
    found = manuals.find("output-mode")
    assert [manuals.name(p) for p in found] == ["glossary/output-mode"]
    assert "integration" in manuals.links(found[0])
    assert manuals.section(found[0]) == "glossary" and manuals.title(found[0]) == "Output mode"
    assert manuals.pages(Path("/nonexistent")) == []


# --- app pieces ----------------------------------------------------------------------


def test_memory_roundtrip(tmp_path):
    memory = Memory(tmp_path / "menu.json")
    memory.put("commands", "stars", {"answers": {"user": "sarverott"}, "mode": "urls"})
    assert Memory(tmp_path / "menu.json").get("commands", "stars")["mode"] == "urls"
    assert Memory(tmp_path / "missing.json").get("tasks", "x") == {}


def test_status_board_renders(tmp_path):
    app = MenuApp(Config(data_dir=tmp_path / "data", datasets_dir=tmp_path / "datasets", github_token=None),
                  root=tmp_path)
    out = themed(100)
    out.print(app.status_board())
    text = out.export_text()
    assert "setup" in text and "GitHub token" in text and "raw buffer" in text
    assert [item.label for item in app.main_items()][-2:] == ["Status", "Quit"]


def test_url_and_json_rendering():
    out = themed(80)
    out.print(MenuApp.render_urls("https://a\n\nhttps://b\n"))
    rows = [line.split() for line in out.export_text().splitlines()]
    assert rows == [["1", "https://a"], ["2", "https://b"]]  # numbered, blank lines dropped
    out.print(MenuApp.render_json('{"a": [1, 2]}'))
    out.print(MenuApp.render_json('{"a": 1}\n{"a": 2}\n'))  # JSON Lines fall back to text


def test_menu_needs_a_terminal(capsys):
    assert main(["menu"]) == 2
    assert "interactive terminal" in capsys.readouterr().err
