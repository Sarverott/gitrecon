"""Contributors from the git log, the ignorelist, AUTHORS text, pies; outward ties of one repository."""

import json
import subprocess
from types import SimpleNamespace

import pytest

from gitrecon.code.relations import custom_registries, outward_ties
from gitrecon.main import main
from gitrecon.mapping import contributors as who
from gitrecon.mapping import score
from gitrecon.mapping.gitgraph import assign_lanes, branch_tips, read_history


def commit(root, name, email, message, text, date):
    (root / f"{date}.txt").write_text(text)
    env = {"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email, "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
           "GIT_AUTHOR_DATE": f"2026-01-{date:02d}T12:00:00+00:00", "GIT_COMMITTER_DATE": f"2026-01-{date:02d}T12:00:00+00:00",
           "PATH": "/usr/bin:/bin", "HOME": str(root)}
    subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True, env=env)
    subprocess.run(["git", "-C", str(root), "commit", "--quiet", "-m", message], check=True, capture_output=True, env=env)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "tool"
    root.mkdir()
    subprocess.run(["git", "-C", str(root), "init", "--quiet", "-b", "master"], check=True, capture_output=True)
    commit(root, "Ann Author", "ann@example.org", "feat: one", "a\nb\nc\n", 1)
    commit(root, "Ann A.", "ann@example.org", "feat: two", "a\n", 2)                         # same address, other spelling
    commit(root, "Ann Author", "ann@work.example", "feat: three", "a\n", 3)                  # same name, other address
    commit(root, "Bob", "bob@example.org", "fix: four\n\nCo-authored-by: Cy <cy@example.org>", "a\nb\n", 4)
    commit(root, "release[bot]", "1+release[bot]@users.noreply.github.com", "bump: version 1 → 2", "a\n", 5)
    return root


def test_contributors_join_names_and_addresses(repo):
    people = who.contributors(repo)
    assert [(p.name, p.commits, p.added, p.co_authored) for p in people] == [
        ("Ann Author", 3, 5, 0), ("Bob", 1, 2, 0), ("release[bot]", 1, 1, 0), ("Cy", 0, 0, 1)]
    ann = people[0]
    assert ann.emails == ["ann@example.org", "ann@work.example"] and ann.names == ["Ann A."]
    assert ann.to_json()["first"] == "2026-01-01" and ann.to_json()["last"] == "2026-01-03"
    assert [p.name for p in who.contributors(repo, max_commits=2)] == ["Bob", "release[bot]", "Cy"]


def test_ignorelist_patterns(tmp_path):
    default = who.read_ignorelist()
    assert "*[bot]" in default and not any(line.startswith("#") for line in default)
    assert who.is_ignored(default, "release[bot]") and who.is_ignored(default, "Dependabot")
    assert not who.is_ignored(default, "Sett Sarverott", "abbot", "robot")       # brackets are plain characters
    own = tmp_path / "ignore.txt"
    own.write_text("# people who asked\nbob@example.org\nAnn *\n")
    patterns = who.read_ignorelist(own)
    assert who.is_ignored(patterns, "Bob", "BOB@example.org") and who.is_ignored(patterns, "ann author")
    assert not who.is_ignored(patterns, "Cy", "")


def test_authors_text_and_pie(repo):
    people = who.contributors(repo, ignore=who.read_ignorelist())
    assert [p.name for p in people] == ["Ann Author", "Bob", "Cy"]
    assert who.authors_text(people, "tool").splitlines()[3:] == [
        "Ann Author <ann@example.org>", "Bob <bob@example.org>", "Cy <cy@example.org>"]    # a co-author is an author
    assert who.contributors_pie(people, "tool") == (
        'pie showData\n    title Commits in tool by contributor\n    "Ann Author" : 3\n    "Bob" : 1\n')
    assert '"Ann Author" : 5' in who.contributors_pie(people, "tool", by="lines")
    assert who.pie({"a": 5, "b": 3, "c": 1, "d": 1, "zero": 0}, 'say "hi"', top=2).splitlines()[1:] == [
        "    title say 'hi'", '    "a" : 5', '    "b" : 3', '    "others (2)" : 2']


def test_contributors_command(repo, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("GITRECON_DATA", str(tmp_path / "data"))
    assert main(["contributors", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "Ann Author <ann@example.org>  (also: Ann A.)" in out and "-- 4 contributors of tool" in out
    assert main(["contributors", str(repo), "--ignorelist", "--format", "authors", "--save"]) == 0
    assert "release[bot]" not in capsys.readouterr().out
    assert "release[bot]" not in (tmp_path / "data" / "contributors" / "tool.AUTHORS").read_text()
    assert main(["contributors", str(repo), "--format", "pie", "--by", "lines", "--save", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["text"].startswith("pie showData") and len(data["contributors"]) == 4
    assert "```mermaid\npie showData" in (tmp_path / "data" / "contributors" / "tool-lines.md").read_text()


def test_score_with_ignorelist_silences_and_unlists(repo):
    commits = read_history(repo)
    assign_lanes(commits, branch_tips(repo))
    notes = score.score_notes(commits, ignore=who.read_ignorelist())
    assert [bool(n.frets) for n in notes] == [True, True, True, True, False]     # the bot's commit keeps its time, silent
    assert [m["author"] for m in score.band(notes)] == ["Ann Author", "Ann A.", "Bob"]   # names as git records them
    tab = score.to_tab(notes, band_mode=True)
    assert "release[bot]" not in tab and "x" not in tab                          # not a rest mark either
    assert len(score.band(score.score_notes(commits))) == 4                      # without the list: the bot too


# --- outward ties ---------------------------------------------------------------------------


def test_outward_ties_in_order_of_firmness(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    (root / "package.json").write_text(json.dumps({"name": "app", "dependencies": {
        "vue": "^3", "@corp/ui": "^1", "otp": "github:me/otp-fork#main", "short": "me/short", "tarball":
        "https://example.org/pkg-1.0.0.tgz", "sibling": "file:../sibling", "app": "*"}}))
    (root / ".npmrc").write_text("@corp:registry=https://npm.corp.example/\nregistry=https://registry.npmjs.org/\n")
    (root / "pyproject.toml").write_text('[project]\nname = "app"\ndependencies = ["requests>=2", '
                                         '"tool @ git+https://github.com/me/tool.git", "app[extra]"]\n'
                                         '[[tool.uv.index]]\nname = "torch"\nurl = "https://download.pytorch.org/whl/cpu"\n')
    (root / "requirements.txt").write_text("--extra-index-url https://pypi.corp.example/simple\nrich\n"
                                           "https://example.org/wheel-1.0-py3-none-any.whl\n")
    (root / "Cargo.toml").write_text('[package]\nname = "app"\n[dependencies]\nserde = "1"\nmine = { git = "https://github.com/me/mine" }\n')
    found = outward_ties(root)
    assert [(t["kind"], t["ecosystem"], t["name"]) for t in found["ties"]] == [
        ("local", "npm", "sibling"),
        ("registry", "cargo", "serde"), ("registry", "npm", "vue"), ("registry", "pypi", "requests"),
        ("registry", "pypi", "rich"),
        ("custom-registry", "npm", "@corp/ui"),
        ("git", "cargo", "mine"), ("git", "npm", "otp"), ("git", "npm", "short"), ("git", "pypi", "tool"),
        ("http", "npm", "tarball"), ("http", "pypi", "wheel-1.0-py3-none-any.whl")]
    assert found["counts"] == {"fork": 0, "local": 1, "registry": 4, "custom-registry": 1, "git": 4, "http": 2}
    assert {r["url"] for r in custom_registries(root)} == {
        "https://npm.corp.example/", "https://download.pytorch.org/whl/cpu", "https://pypi.corp.example/simple"}
    assert found["notes"] == ["no origin remote: whether it is a fork cannot be asked"]


def test_fork_parent_comes_first(tmp_path):
    root = tmp_path / "otp"
    root.mkdir()
    (root / "package.json").write_text(json.dumps({"dependencies": {"vue": "^3"}}))
    subprocess.run(["git", "-C", str(root), "init", "--quiet"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", "git@github.com:me/otp.git"], check=True)
    parent = {"fork": True, "parent": {"full_name": "upstream/otp", "html_url": "https://github.com/upstream/otp"}}
    client = SimpleNamespace(get=lambda path: SimpleNamespace(data=parent if path == "/repos/me/otp" else {}))
    ties = outward_ties(root, client)["ties"]
    assert (ties[0]["kind"], ties[0]["name"]) == ("fork", "upstream/otp") and ties[1]["kind"] == "registry"
    assert main(["relations", str(root), "--offline", "--format", "mermaid"]) == 0
