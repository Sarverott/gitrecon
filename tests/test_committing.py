"""Committing per file: changes, their order, the form, handlers, the plan and applying it."""

import json
import subprocess

import pytest

from gitrecon import committing
from gitrecon.committing import ChangeContext, build_message, form_fields, plan_commits
from gitrecon.main import main


def test_build_message_is_always_a_conventional_commit():
    assert build_message({"prefix": "feat", "scope": "cli tools", "subject": "Add the thing.", "body": "Because."}) == (
        "feat(cli-tools): add the thing\n\nBecause.")
    assert build_message({"prefix": "fix", "subject": "x" * 200}).splitlines()[0] == "fix: " + "x" * 72
    assert build_message({"prefix": "chore", "scope": "", "subject": "update lock"}) == "chore: update lock"
    breaking = build_message({"prefix": "feat", "subject": "drop v1", "is_breaking_change": True, "body": "v1 is gone"})
    assert "BREAKING CHANGE: v1 is gone" in breaking
    with pytest.raises(ValueError):
        build_message({"prefix": "feature", "subject": "x"})


def test_form_fields_describe_what_a_handler_answers():
    fields = form_fields()
    assert [f["name"] for f in fields] == ["prefix", "scope", "subject", "body", "is_breaking_change", "footer"]
    prefix, breaking = fields[0], fields[4]
    assert prefix["kind"] == "choice" and {"feat", "fix", "docs", "chore"} <= set(prefix["choices"])
    assert breaking["kind"] == "yes/no" and fields[2]["kind"] == "text"


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "proj"
    (root / "pkg").mkdir(parents=True)
    (root / "tests").mkdir()
    git = lambda *a: subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *a],  # noqa: E731
                                    check=True, capture_output=True, text=True).stdout
    git("init", "--quiet", "-b", "development")
    (root / "pkg" / "__init__.py").write_text("")
    (root / "pkg" / "core.py").write_text("def add(a, b):\n    return a - b\n")
    (root / "old.txt").write_text("x\n")
    (root / "README.md").write_text("# proj\n")
    git("add", ".")
    git("commit", "--quiet", "-m", "feat: start")
    # the changes: a fix, a new module using it, a test, docs, a deletion
    (root / "pkg" / "core.py").write_text("def add(a, b):\n    return a + b\n")
    (root / "pkg" / "app.py").write_text("from pkg.core import add\n\nprint(add(1, 2))\n")
    (root / "tests" / "test_core.py").write_text("from pkg.core import add\n\ndef test_add():\n    assert add(1, 2) == 3\n")
    (root / "README.md").write_text("# proj\n\nAdds numbers.\n")
    (root / "old.txt").unlink()
    return root, git


def test_changes_and_their_order(repo):
    root, git = repo
    changes = committing.changed_files(root)
    assert {(c.path, c.status) for c in changes} == {
        ("pkg/core.py", "modified"), ("pkg/app.py", "added"), ("tests/test_core.py", "added"),
        ("README.md", "modified"), ("old.txt", "deleted")}
    ordered = [c.path for c in committing.order_changes(root, changes)]
    assert ordered == ["pkg/core.py", "pkg/app.py", "tests/test_core.py", "README.md", "old.txt"]   # what is imported first
    diff = committing.file_diff(root, changes[[c.path for c in changes].index("pkg/core.py")])
    assert "-    return a - b" in diff and "+    return a + b" in diff
    assert committing.file_diff(root, committing.Change("pkg/app.py", "added")).startswith("+from pkg.core import add")
    # renamed in the index and then removed: the old file is simply gone
    git("mv", "README.md", "GUIDE.md")
    (root / "GUIDE.md").unlink()
    assert ("README.md", "deleted") in {(c.path, c.status) for c in committing.changed_files(root)}


def test_the_path_handler_and_the_plan(repo):
    root, _ = repo
    plan = plan_commits(root)
    assert [(s["message"], s["by"]) for s in plan] == [
        ("chore(pkg): update core.py", "path"), ("chore(pkg): add app.py", "path"),
        ("test(tests): add test_core.py", "path"), ("docs: update README.md", "path"), ("docs: remove old.txt", "path")]
    assert plan[0]["facts"] == {"path": "pkg/core.py", "status": "modified", "language": "Python", "kind": "code",
                                "lines_added": 1, "lines_deleted": 1}
    assert "note" not in plan[0] and len(plan_commits(root, limit=2)) == 2
    assert sorted(committing.HANDLERS) == ["path"]


def test_a_handler_gets_the_context_and_its_answers_become_the_message(repo):
    root, _ = repo
    seen: list[ChangeContext] = []

    def careful(context: ChangeContext):
        seen.append(context)
        if context.change.path == "pkg/core.py":
            assert "+    return a + b" in context.diff
            return {"prefix": "fix", "scope": "core", "subject": "Add the operands instead of subtracting them."}
        if context.change.path == "pkg/app.py":
            return None                                    # passes
        if context.change.path == "README.md":
            return {"prefix": "nonsense", "subject": "x"}  # not a valid message
        raise RuntimeError("no idea")

    plan = plan_commits(root, handler=careful)
    assert [(s["path"], s["by"], s.get("note")) for s in plan] == [
        ("pkg/core.py", "careful", None), ("pkg/app.py", "path", "careful passed"),
        ("tests/test_core.py", "path", "no idea"), ("README.md", "path", "not a Conventional Commit: 'nonsense: x'"),
        ("old.txt", "path", "no idea")]
    assert plan[0]["message"] == "fix(core): add the operands instead of subtracting them"
    first = seen[0]
    assert (first.position, first.total, first.repo) == (0, 5, root)
    assert first.facts["used_by"] == 2 and first.facts["imports"] == []          # relations, for handlers that read
    assert [f["name"] for f in first.form][:3] == ["prefix", "scope", "subject"]


def test_registered_handlers_are_choosable_by_name(repo, monkeypatch):
    root, _ = repo
    monkeypatch.setattr(committing.handlers, "HANDLERS", dict(committing.HANDLERS))

    @committing.register("shout")
    def shout(context):
        return {"prefix": "docs", "subject": f"touch {context.change.path}"}

    assert committing.handlers.HANDLERS["shout"] is shout
    monkeypatch.setattr("gitrecon.committing.plan.HANDLERS", committing.handlers.HANDLERS)
    assert plan_commits(root, handler="shout", limit=1)[0]["message"] == "docs: touch pkg/core.py"


def test_apply_makes_one_commit_per_file(repo):
    root, git = repo
    (root / "untouched.txt").write_text("left alone\n")
    plan = [s for s in plan_commits(root) if s["path"] != "untouched.txt"]
    done = committing.apply_plan(root, plan)
    assert all(step["committed"] for step in done) and len(done) == 5
    assert git("log", "--format=%s").splitlines()[:5] == ["docs: remove old.txt", "docs: update README.md",
                                                           "test(tests): add test_core.py", "chore(pkg): add app.py",
                                                           "chore(pkg): update core.py"]
    assert git("show", "--stat", "--format=", "HEAD~1").count("|") == 1          # one file in each commit
    assert git("status", "--porcelain").strip() == "?? untouched.txt"            # the rest of the tree is as it was


def test_commit_files_command(repo, capsys):
    root, git = repo
    assert main(["commit-files", str(root), "--limit", "2"]) == 0
    out = capsys.readouterr().out
    assert "modified  pkg/core.py" in out and "a plan of 2 commits; nothing was committed" in out
    assert git("log", "--oneline").count("\n") == 1                            # still only the first commit
    assert main(["commit-files", str(root), "--apply", "--json"]) == 0
    assert len([s for s in json.loads(capsys.readouterr().out) if s["committed"]]) == 5
    assert main(["commit-files", str(root)]) == 0 and "nothing changed" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["commit-files", str(root), "--handler", "no-such-handler"])
    with pytest.raises(SystemExit):
        main(["llm", "models"])                                                # parked


def test_commitizen_does_not_silence_our_loggers():
    import logging

    ours = logging.getLogger("gitrecon.sources.github_api")
    ours.disabled = False
    committing.commit_types()
    build_message({"prefix": "feat", "subject": "x"})
    assert not ours.disabled


def test_save_is_one_commit_with_a_message_from_the_paths(repo, capsys):
    root, git = repo
    message = committing.save_message(root)
    assert message.splitlines()[0] == "chore: save 5 files (pkg 2, root 2, tests 1)"
    assert "modified: pkg/core.py" in message and "deleted: old.txt" in message
    assert main(["commit-files", str(root), "--single"]) == 0               # shows the message, commits nothing
    assert git("log", "--oneline").count("\n") == 1
    assert main(["commit-files", str(root), "--single", "--apply"]) == 0
    assert "saved as " in capsys.readouterr().out
    assert git("log", "-1", "--format=%s").strip() == "chore: save 5 files (pkg 2, root 2, tests 1)"
    assert git("status", "--porcelain") == "" and committing.save_message(root) is None
    (root / "README.md").write_text("# proj\n\nmore\n")
    assert committing.save_message(root).splitlines()[0] == "docs: save 1 file (root 1)"    # all files agree: docs
