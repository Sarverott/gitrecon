"""BOS routines: the things done the same way around every commit, switched by .husky/bos.config.json.

Commands (run from the repository root):
  add-all    stage everything (git add -A)        flag: auto_gitaddall_before_commit
  push       push the branch after a commit       flag: auto_push_after_commit
  explain    print which routines are on

BOS_SKIP_ROUTINES=add-all,push in the environment switches routines off for one command.

Git refuses to commit before any hook runs when nothing is staged, so add-all must run
before the commit command (task commit does that). The pre-commit hook runs it as well,
which picks up the rest when only some changes were staged.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

CONFIG = Path(".husky/bos.config.json")

ROUTINES = {
    "add-all": "auto_gitaddall_before_commit",
    "push": "auto_push_after_commit",
}

# canon is only reached through the loop's pull requests, never pushed to directly
PROTECTED_BRANCHES = {"master"}


def skipped(name):
    """BOS_SKIP_ROUTINES=add-all,push switches routines off for one command (a series of per-file commits)."""
    return name in {part.strip() for part in os.environ.get("BOS_SKIP_ROUTINES", "").split(",")}


def enabled(flag):
    if not CONFIG.exists():
        return False
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    return bool(config.get("routines", {}).get("flags", {}).get(flag, False))


def git(*args, check=True):
    return subprocess.run(["git", *args], check=check, text=True, capture_output=True)


def operation_in_progress():
    """Rebase, merge, cherry-pick or revert: commits made inside them must not be pushed one by one."""
    git_dir = Path(git("rev-parse", "--git-dir").stdout.strip())
    markers = ["rebase-merge", "rebase-apply", "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD"]
    return next((m for m in markers if (git_dir / m).exists()), None)


def routine_add_all():
    if not enabled(ROUTINES["add-all"]) or skipped("add-all"):
        return
    git("add", "-A")
    print("routine add-all: staged all changes")


def routine_push():
    if not enabled(ROUTINES["push"]) or skipped("push"):
        return
    branch = git("branch", "--show-current").stdout.strip()
    if not branch:
        print("routine push: detached HEAD, not pushing")
        return
    if branch in PROTECTED_BRANCHES:
        print(f"routine push: {branch} is canon, it only changes through the loop, not pushing")
        return
    if operation := operation_in_progress():
        print(f"routine push: {operation} in progress, not pushing")
        return
    has_upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", check=False).returncode == 0
    args = ["push"] if has_upstream else ["push", "--set-upstream", "origin", branch]
    result = git(*args, check=False)
    if result.returncode == 0:
        print(f"routine push: pushed {branch}")
    else:
        # the commit is already made; a failed push must not look like a failed commit
        print(f"routine push: push of {branch} failed, push it by hand:\n{result.stderr.strip()}", file=sys.stderr)


def routine_explain():
    for name, flag in ROUTINES.items():
        print(f"  {name:8} {flag:30} {'on' if enabled(flag) else 'off'}")


def main():
    commands = {"add-all": routine_add_all, "push": routine_push, "explain": routine_explain}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        raise SystemExit(__doc__)
    commands[sys.argv[1]]()


if __name__ == "__main__":
    main()
