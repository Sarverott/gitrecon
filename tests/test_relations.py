"""CaptorLex step 2, second circle: ties between the repositories of one owner."""

import json
import subprocess

import pytest

from gitrecon.code.relations import owner_relations, published_names, relations_mermaid, submodules
from gitrecon.main import main


def make_repo(folder, name, files, remote_owner="Rattish"):
    root = folder / name
    root.mkdir(parents=True)
    for file, text in files.items():
        (root / file).parent.mkdir(parents=True, exist_ok=True)
        (root / file).write_text(text)
    run = lambda *a: subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True)  # noqa: E731
    run("init", "--quiet")
    run("add", ".")
    run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "-m", "feat: x")
    run("remote", "add", "origin", f"https://github.com/{remote_owner}/{name}.git")
    return root


GITMODULES = """[submodule "tools with spaces"]
\tpath = .devtools/chainer
\turl = https://github.com/rattish/Chainer.git
[submodule "sibling"]
\tpath = vendor/docs
\turl = ../docs-builder.git
[submodule "elsewhere"]
\tpath = vendor/lib
\turl = git@github.com:someone/lib.git
"""


@pytest.fixture
def forge(tmp_path):
    owner = tmp_path / "rattish"
    make_repo(owner, "core", {
        ".gitmodules": GITMODULES,
        "package.json": json.dumps({"name": "@rattish/core", "dependencies": {
            "rat-gui": "^1", "left-pad": "1", "rat-cli": "github:rattish/cli#main"}}),
        "pyproject.toml": '[project]\nname = "rat_core"\ndependencies = ["Rat-Parser>=1", "requests"]\n',
    })
    make_repo(owner, "Chainer", {"README.md": "x"})
    make_repo(owner, "docs-builder", {"README.md": "x"})
    make_repo(owner, "gui", {"package.json": json.dumps({"name": "rat-gui", "dependencies": {"@rattish/core": "*"}})})
    make_repo(owner, "parser", {"pyproject.toml": '[project]\nname = "rat-parser"\n', "go.mod": "module github.com/rattish/parser\n"})
    make_repo(owner, "cli", {"go.mod": "module x\n\nrequire (\n\tgithub.com/rattish/parser/v2 v2.0.0\n)\n"})
    make_repo(owner, "alone", {"README.md": "x"})
    (owner / "not-a-repo").mkdir()
    return owner


def test_published_names_and_submodules(forge):
    assert published_names(forge / "core") == {"npm": "@rattish/core", "pypi": "rat-core"}
    assert published_names(forge / "parser") == {"pypi": "rat-parser", "go": "github.com/rattish/parser"}
    assert submodules(forge / "core") == [
        {"path": "vendor/lib", "url": "git@github.com:someone/lib.git"},
        {"path": "vendor/docs", "url": "../docs-builder.git"},
        {"path": ".devtools/chainer", "url": "https://github.com/rattish/Chainer.git"}]   # names with spaces survive
    assert submodules(forge / "alone") == []


def test_ties_submodules_first_then_dependencies(forge):
    relations = owner_relations(forge)
    assert [r["name"] for r in relations["repositories"]] == ["Chainer", "alone", "cli", "core", "docs-builder", "gui",
                                                             "parser"]
    assert [(e["kind"], e["from"], e["to"], e["detail"]) for e in relations["edges"]] == [
        ("submodule", "core", "Chainer", ".devtools/chainer"),
        ("submodule", "core", "docs-builder", "vendor/docs"),            # a relative URL: the same owner
        ("dependency", "cli", "parser", "go: github.com/rattish/parser/v2"),
        ("dependency", "core", "cli", "git URL in package.json"),
        ("dependency", "core", "gui", "npm: rat-gui"),
        ("dependency", "core", "parser", "pypi: rat-parser"),            # Rat-Parser, rat_parser, rat-parser: one name
        ("dependency", "gui", "core", "npm: @rattish/core")]
    assert relations["outside_submodules"] == [{"from": "core", "url": "git@github.com:someone/lib.git",
                                                "path": "vendor/lib"}]
    assert relations["untied"] == ["alone"]


def test_mermaid_and_command(forge, capsys, monkeypatch, tmp_path):
    relations = owner_relations(forge)
    diagram = relations_mermaid(relations)
    assert 'r_core ==>|"submodule: .devtools/chainer"| r_Chainer' in diagram
    assert 'r_core -.->|"dependency: npm: rat-gui"| r_gui' in diagram
    assert 'out_0("someone/lib"):::outside' in diagram and 'r_alone["alone"]' not in diagram
    assert 'r_alone["alone"]' in relations_mermaid(relations, show_untied=True)

    monkeypatch.setenv("GITRECON_DATA", str(tmp_path / "data"))
    assert main(["relations", str(forge), "--save"]) == 0
    out = capsys.readouterr().out
    assert "rattish: 7 repositories, 2 submodule ties, 5 dependency ties between them" in out
    assert "submodules from outside the folder: 1" in out and "untied: 1 (alone)" in out
    assert "```mermaid\nflowchart LR" in (tmp_path / "data" / "relations" / "rattish.md").read_text()
    assert main(["relations", str(forge), "--json"]) == 0
    assert set(json.loads(capsys.readouterr().out)) >= {"repositories", "edges", "outside_submodules", "untied", "mermaid"}
    assert main(["relations", str(forge / "not-a-repo")]) == 2
