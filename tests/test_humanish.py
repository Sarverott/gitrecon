"""Humanish level 1 (commit messages, requirement keywords) and translation - offline."""

import json
import subprocess
from types import SimpleNamespace

import pytest

from gitrecon.analysis.labeler import Labeler
from gitrecon.humanish import commit_labels, find_requirements, parse_commit, summarize_commits
from gitrecon.humanish.commits import meanings
from gitrecon.main import main

# --- commit messages -------------------------------------------------------------------


@pytest.mark.parametrize(("message", "form", "type_", "scope", "subject"), [
    ("feat(cli): add gitgraph", "conventional", "feat", "cli", "add gitgraph"),
    ("FIX: typo", "conventional", "fix", None, "typo"),
    ("feat(adding-a,-adding-b): two things, at once", "conventional", "feat", "adding-a,-adding-b",
     "two things, at once"),
    ("bump: version 0.3.4 → 0.4.0", "conventional", "bump", None, "version 0.3.4 → 0.4.0"),
    ("Merge pull request #7 from user/feature/x", "merge", None, None, "#7 from user/feature/x"),
    ("Merge branch 'development' into revision", "merge", None, None, "'development' into revision"),
    ('Revert "feat: x"', "revert", "revert", None, '"feat: x"'),
    ("Initial commit", "plain", None, None, "Initial commit"),
    ("fix:no space after the colon", "plain", None, None, "fix:no space after the colon"),
    ("Update README.md: typo", "plain", None, None, "Update README.md: typo"),
    ("", "plain", None, None, ""),
])
def test_commit_header_forms(message, form, type_, scope, subject):
    commit = parse_commit(message)
    assert (commit.form, commit.type, commit.scope, commit.subject) == (form, type_, scope, subject)


def test_breaking_mark_trailers_and_work():
    commit = parse_commit("feat(api)!: drop v1\n\nlong explanation here\n\nBREAKING CHANGE: v1 is gone\n"
                          "Co-Authored-By: A <a@b.c>\nRefs #12\n", sha="abc")
    assert commit.breaking and commit.work == "feature" and commit.sha == "abc"
    assert commit.trailers == {"BREAKING CHANGE": ["v1 is gone"], "Co-Authored-By": ["A <a@b.c>"], "Refs": ["12"]}
    assert parse_commit("fix: x\n\nBREAKING CHANGE: y").breaking          # by trailer alone
    assert parse_commit("wip: x").work is None                           # a type humanish.yml does not know
    assert parse_commit('Revert "feat: x"').work == "fix"


def test_every_commit_type_has_work_and_meaning():
    for name, spec in meanings()["commit_types"].items():
        assert set(spec) == {"work", "meaning"}, name
    assert set(meanings()["requirement_levels"]) == {"OBLIGATION", "PROHIBITION", "RECOMMENDATION", "DISCOURAGEMENT",
                                                     "PERMISSION"}


def history(*messages):
    return [parse_commit(m, sha=f"{n:040x}") for n, m in enumerate(messages)]


def test_summary_and_labels():
    commits = history(*["feat: a"] * 3, *["fix: b"] * 6, *["bump: version 1 → 2"] * 3, "fix(x)!: c", "notes",
                      "Merge branch 'x'", "wip: y")
    summary = summarize_commits(commits)
    assert (summary["commits"], summary["own"], summary["breaking"]) == (16, 15, 1)
    assert summary["forms"] == {"conventional": 14, "plain": 1, "merge": 1}
    assert summary["conventional_share"] == 0.933 and summary["types"]["fix"] == 7
    assert summary["work"] == {"fix": 7, "feature": 3, "delivery": 3, "unknown": 1}
    assert summary["scopes"] == {"x": 1} and summary["unknown_types"] == ["wip"]
    labels = {label.name: label for label in commit_labels("repo:a/b", commits)}
    assert set(labels) == {"conventional-commits", "fix-heavy", "release-automation", "breaking-changes"}
    assert labels["conventional-commits"].confidence == 0.93 and labels["fix-heavy"].details["fixes"] == 7
    assert len(labels["release-automation"].evidence) == 3
    assert labels["breaking-changes"].html_url == "https://github.com/a/b"


def test_too_few_commits_conclude_nothing():
    assert commit_labels("repo:a/b", history(*["feat!: a"] * 9)) == []


def test_labeler_reads_commit_messages_of_pushes():
    push = {"id": "1", "type": "PushEvent", "created_at": "2026-01-01T00:00:00Z", "actor": {"login": "me"},
            "repo": {"name": "a/b"},
            "payload": {"commits": [{"sha": f"{n:040x}", "message": "feat: x"} for n in range(12)]}}
    labeler = Labeler()
    labeler.ingest([push, push | {"id": "2", "payload": {}}])        # current pushes carry no commits: ignored
    found = [label for label in labeler.run() if label.name == "conventional-commits"]
    assert [(label.target, label.confidence) for label in found] == [("repo:a/b", 1.0)]


def test_commits_command(tmp_path, capsys):
    run = lambda *a: subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)  # noqa: E731
    run("init", "--quiet")
    for n in range(11):
        run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "--allow-empty", "-m",
            f"feat(part{n % 2}): step {n}")
    run("remote", "add", "origin", "git@github.com:Me/Tool.git")
    assert main(["commits", str(tmp_path), "--list"]) == 0
    out = capsys.readouterr().out
    assert "conventional form: 100% of 11 own commits" in out and "scopes: part0 6, part1 5" in out
    assert "[conventional-commits] repo:me/tool (1.00, 11 evidence)" in out and "step 10" in out
    assert main(["commits", str(tmp_path), "--max-commits", "3", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["commits"] == 3 and data["labels"] == [] and data["commits"] is None


# --- requirement keywords ----------------------------------------------------------------

TEXT = """1.1 Scope

A client MUST send the header, e.g. X-A, in v1.2 too. It MAY retry. Servers SHOULD NOT cache
the answer and MUST NOT log it! MAYBE later, and a must in small letters. This is NOT RECOMMENDED

The key words "MUST" and 'SHOULD' are explained elsewhere.
The field is OPTIONAL"""


def test_requirement_sentences():
    found = [(r.level, r.keywords, r.line) for r in find_requirements(TEXT)]
    assert found == [("obligation", ["MUST"], 3), ("permission", ["MAY"], 3),
                     ("prohibition", ["SHOULD NOT", "MUST NOT"], 3), ("discouragement", ["NOT RECOMMENDED"], 4),
                     ("permission", ["OPTIONAL"], 7)]
    first = find_requirements(TEXT)[0]
    assert first.sentence == "A client MUST send the header, e.g. X-A, in v1.2 too."   # abbreviations do not end it
    assert find_requirements("no keywords here.\x0c\r\n\r\nNone at all") == []          # page breaks, CRLF


def test_text_requirements_command(tmp_path, capsys):
    path = tmp_path / "spec.txt"
    path.write_text(TEXT)
    assert main(["text", "requirements", str(path), "--raw"]) == 0
    out = capsys.readouterr().out
    assert "prohibition    line 3" in out and "-- 2 permission, 1 obligation, 1 prohibition, 1 discouragement" in out
    assert main(["text", "requirements", str(path), "--raw", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["keywords"] == ["MUST"]


# --- translation (Argos faked: no models in tests) ---------------------------------------------


class FakeLanguage:
    def __init__(self, code, name, to=()):
        self.code, self.name, self._to = code, name, set(to)

    def get_translation(self, other):
        if other.code in self._to:
            return SimpleNamespace(translate=lambda text: f"[{self.code}>{other.code}] {text}")
        return None


class FakePackage(SimpleNamespace):
    def download(self):
        return f"/tmp/{self.from_code}_{self.to_code}.argosmodel"


@pytest.fixture
def argos(monkeypatch):
    package = lambda a, b: FakePackage(from_code=a, from_name=a.upper(), to_code=b, to_name=b.upper(),  # noqa: E731
                                       package_version="1.9")
    state = SimpleNamespace(installed=[], paths=[], refreshed=0)
    fake = SimpleNamespace(
        package=SimpleNamespace(
            get_installed_packages=lambda: state.installed,
            get_available_packages=lambda: [package("en", "pl"), package("pl", "en")],
            update_package_index=lambda: setattr(state, "refreshed", state.refreshed + 1),
            install_from_path=lambda path: (state.paths.append(path), state.installed.append(package("en", "pl")))),
        translate=SimpleNamespace(get_installed_languages=lambda: (
            [FakeLanguage("en", "English", to=["pl"]), FakeLanguage("pl", "Polish")] if state.installed else [])))
    monkeypatch.setattr("gitrecon.translate.argos._argos", lambda: fake)
    return state


def test_install_list_translate(argos):
    from gitrecon.translate import available_packages, install, installed_languages, translate

    assert [(p["from"], p["to"]) for p in available_packages()] == [("en", "pl"), ("pl", "en")]
    assert installed_languages() == []
    with pytest.raises(LookupError, match="gitrecon translate install en pl"):
        translate("hello", "en", "pl")
    assert install("en", "pl")["status"] == "installed" and argos.paths == ["/tmp/en_pl.argosmodel"]
    assert install("en", "pl")["status"] == "exists" and len(argos.paths) == 1
    with pytest.raises(LookupError, match="no package xx -> pl"):
        install("xx", "pl")
    assert installed_languages() == [{"code": "en", "name": "English", "to": ["pl"]},
                                     {"code": "pl", "name": "Polish", "to": []}]
    assert translate("hello", "en", "pl") == "[en>pl] hello"


def test_translate_command(argos, capsys, monkeypatch):
    assert main(["translate", "text", "--from", "en", "--to", "pl", "hello", "world"]) == 1   # nothing installed
    assert "gitrecon translate install en pl" in capsys.readouterr().out
    assert main(["translate", "install", "en", "pl"]) == 0
    assert "installed: EN -> PL" in capsys.readouterr().out
    assert main(["translate", "languages"]) == 0
    assert "en   English                -> pl" in capsys.readouterr().out
    assert main(["translate", "text", "--from", "en", "--to", "pl", "hello", "world", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["translation"] == "[en>pl] hello world"
    assert main(["translate", "install", "en"]) == 2 and main(["translate", "text", "hello"]) == 2
