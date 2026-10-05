"""Saving the working tree as one commit with a message written from the changed files."""

import json
import subprocess

import pytest

from gitrecon import committing
from gitrecon.main import main


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "proj"
    (root / "pkg").mkdir(parents=True)
    (root / "tests").mkdir()
    git = lambda *a: subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *a],  # noqa: E731
                                    check=True, capture_output=True, text=True).stdout
    git("init", "--quiet", "-b", "development")
    git("config", "user.name", "t")
    git("config", "user.email", "t@t")
    (root / "pkg" / "core.py").write_text("def add(a, b):\n    return a - b\n")
    (root / "old.txt").write_text("x\n")
    (root / "README.md").write_text("# proj\n")
    git("add", ".")
    git("commit", "--quiet", "-m", "feat: start")
    (root / "pkg" / "core.py").write_text("def add(a, b):\n    return a + b\n")
    (root / "pkg" / "app.py").write_text("from pkg.core import add\n")
    (root / "tests" / "test_core.py").write_text("def test_add(): pass\n")
    (root / "README.md").write_text("# proj\n\nAdds numbers.\n")
    (root / "old.txt").unlink()
    return root, git


def test_changed_files(repo):
    root, git = repo
    assert committing.changed_files(root) == [
        ("modified", "README.md"), ("deleted", "old.txt"), ("added", "pkg/app.py"), ("modified", "pkg/core.py"),
        ("added", "tests/test_core.py")]
    git("mv", "README.md", "GUIDE.md")            # renamed in the index and then removed: the old file is gone
    (root / "GUIDE.md").unlink()
    assert ("deleted", "README.md") in committing.changed_files(root)


@pytest.mark.parametrize(("path", "kind"), [
    (".github/workflows/x.yml", "ci"), ("tests/test_a.py", "test"), ("docs/guide.md", "docs"), ("README.md", "docs"),
    ("pyproject.toml", "build"), ("src/gitrecon/cli/content.py", "chore")])
def test_kind_of(path, kind):
    assert committing.kind_of(path) == kind


def test_save_message(repo):
    root, _ = repo
    message = committing.save_message(root)
    assert message.splitlines()[0] == "chore: save 5 files (pkg 2, root 2, tests 1)"
    assert message.splitlines()[2:] == ["modified: README.md", "deleted: old.txt", "added: pkg/app.py",
                                        "modified: pkg/core.py", "added: tests/test_core.py"]


def test_save_command(repo, capsys):
    root, git = repo
    assert main(["save", str(root), "--dry-run"]) == 0                      # shows the message, commits nothing
    assert capsys.readouterr().out.startswith("chore: save 5 files")
    assert git("log", "--oneline").count("\n") == 1
    assert main(["save", str(root), "--json"]) == 0
    done = json.loads(capsys.readouterr().out)
    assert done["committed"] and done["sha"] and done["error"] is None
    assert git("log", "-1", "--format=%s").strip() == "chore: save 5 files (pkg 2, root 2, tests 1)"
    assert git("status", "--porcelain") == "" and committing.save_message(root) is None
    assert main(["save", str(root)]) == 0 and "nothing to save" in capsys.readouterr().out
    (root / "README.md").write_text("# proj\n\nmore\n")
    assert committing.save_message(root).splitlines()[0] == "docs: save 1 file (root 1)"    # all files agree: docs


def test_a_refused_commit_is_reported(repo, capsys):
    root, git = repo
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho no thanks >&2\nexit 1\n")
    hook.chmod(0o755)
    assert main(["save", str(root)]) == 1
    assert "NOT saved" in capsys.readouterr().out and git("log", "--oneline").count("\n") == 1
