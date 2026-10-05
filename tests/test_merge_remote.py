"""The merge procedure (scripts/merge_remote.py) on throwaway repositories with a local remote."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "merge_remote.py"


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
                          cwd=cwd, check=True, capture_output=True, text=True).stdout


def commit(cwd, name, text, message):
    (cwd / name).write_text(text)
    git(cwd, "add", ".")
    git(cwd, "commit", "--quiet", "-m", message)


def procedure(cwd, *args):
    done = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin", "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "HOME": str(cwd)})
    return done.returncode, done.stdout + done.stderr


@pytest.fixture
def pair(tmp_path):
    """``mine`` and ``other``: two clones of one bare remote, both on ``development`` with one commit."""
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--quiet", "--bare", "-b", "development", str(remote))
    mine, other = tmp_path / "mine", tmp_path / "other"
    git(tmp_path, "clone", "--quiet", str(remote), str(mine))
    git(mine, "checkout", "--quiet", "-b", "development")
    commit(mine, "a.txt", "one\n", "feat: a")
    git(mine, "push", "--quiet", "-u", "origin", "development")
    git(tmp_path, "clone", "--quiet", str(remote), str(other))
    return mine, other


def push_from(other, name, text, message="bump: version 1 → 2"):
    commit(other, name, text, message)
    git(other, "push", "--quiet")


def test_up_to_date_and_waiting_to_push(pair):
    mine, _ = pair
    assert procedure(mine) == (0, "fetching origin ...\ndevelopment: 0 commit(s) only here, 0 only on "
                                  "origin/development\nup to date with the remote.\n")
    commit(mine, "b.txt", "x\n", "feat: b")
    assert "1 commit(s) wait to be pushed" in procedure(mine)[1]


def test_fast_forward(pair):
    mine, other = pair
    push_from(other, "version.txt", "2\n")
    code, out = procedure(mine, "--check")
    assert code == 0 and "a fast-forward" in out and not (mine / "version.txt").exists()   # looked only
    code, out = procedure(mine)
    assert code == 0 and (mine / "version.txt").read_text() == "2\n"
    assert git(mine, "rev-list", "--merges", "--count", "HEAD").strip() == "0"


def test_diverged_clean_merge(pair):
    mine, other = pair
    push_from(other, "version.txt", "2\n")
    commit(mine, "b.txt", "x\n", "feat: b")
    code, out = procedure(mine, "--check")
    assert code == 0 and "1 commit(s) only here, 1 only on origin/development" in out and "the merge is clean" in out
    code, out = procedure(mine)
    assert code == 0 and "merged origin/development into development" in out and "undo:    git reset --hard" in out
    assert (mine / "version.txt").exists() and (mine / "b.txt").exists()
    assert git(mine, "log", "-1", "--format=%s").strip() == "Merge remote-tracking branch 'origin/development' into development"
    assert git(mine, "rev-list", "--count", "origin/development..HEAD").strip() == "2"      # nothing was pushed


def test_conflict_is_reported_before_anything_changes(pair):
    mine, other = pair
    push_from(other, "a.txt", "theirs\n")
    commit(mine, "a.txt", "ours\n", "fix: a")
    head = git(mine, "rev-parse", "HEAD")
    code, out = procedure(mine, "--check")
    assert code == 1 and "conflicts in 1 file(s)" in out and "  a.txt" in out
    assert git(mine, "rev-parse", "HEAD") == head and git(mine, "status", "--porcelain") == ""
    code, out = procedure(mine)
    assert code == 1 and "need your decision" in out and "git merge --abort" in out
    assert "<<<<<<<" in (mine / "a.txt").read_text()
    assert "a merge is already in progress" in procedure(mine)[1]
    git(mine, "merge", "--abort")
    assert (mine / "a.txt").read_text() == "ours\n"


def test_lockfile_conflicts_take_the_remote_side(pair):
    mine, other = pair
    push_from(other, "package-lock.json", '{"version": "2"}\n')
    commit(mine, "package-lock.json", '{"version": "1-local"}\n', "feat: dependency")
    code, out = procedure(mine)
    assert code == 0 and "settled automatically" in out
    assert (mine / "package-lock.json").read_text() == '{"version": "2"}\n'


def test_dirty_tree_is_refused(pair):
    mine, other = pair
    push_from(other, "version.txt", "2\n")
    (mine / "scratch.txt").write_text("unsaved")
    code, out = procedure(mine)
    assert code != 0 and "uncommitted changes in the way" in out and not (mine / "version.txt").exists()
