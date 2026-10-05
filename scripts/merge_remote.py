#!/usr/bin/env python3
"""Bring the remote version of the current branch into the local one - safely.

    task merge:check     look only: how far apart, would it conflict, in which files
    task merge:remote    do it: fast-forward, or merge when both sides have commits

Why it is needed: the loop ends with master merged back into development on GitHub (version
bump, changelog). A commit made locally before pulling that makes the two diverge, and the
push after the commit is refused.

What it does, in order: fetch; compare; refuse to work on a dirty tree; try the merge in
memory first (nothing is touched when that shows conflicts and --check is given); merge;
re-lock uv.lock when the merge left it stale. It never pushes and never rewrites commits.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REGENERATED = ("uv.lock", "package-lock.json")  # conflicts here are settled by taking the remote side and re-locking


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    done = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if check and done.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{done.stderr.strip() or done.stdout.strip()}")
    return done


def say(text: str = "") -> None:
    print(text, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="look only, change nothing")
    parser.add_argument("--remote", default="origin")
    args = parser.parse_args()

    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch == "HEAD":
        sys.exit("not on a branch (detached HEAD, or in the middle of a rebase)")
    if git("rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0:
        sys.exit("a merge is already in progress: resolve the files `git status` lists, `git add` them, "
                 "then `git merge --continue` - or give up with `git merge --abort`")
    upstream = f"{args.remote}/{branch}"

    say(f"fetching {args.remote} ...")
    git("fetch", "--prune", args.remote)
    if git("rev-parse", "-q", "--verify", upstream, check=False).returncode != 0:
        say(f"{upstream} does not exist: the branch was never pushed. Nothing to merge; `git push -u {args.remote} {branch}`.")
        return 0
    ahead, behind = map(int, git("rev-list", "--left-right", "--count", f"{branch}...{upstream}").stdout.split())
    say(f"{branch}: {ahead} commit(s) only here, {behind} only on {upstream}")
    if behind == 0:
        say("up to date with the remote." + (f" {ahead} commit(s) wait to be pushed: `git push`." if ahead else ""))
        return 0

    for line in git("log", "--oneline", "--no-merges", f"{branch}..{upstream}").stdout.splitlines()[:15]:
        say(f"  remote: {line}")
    dirty = git("status", "--porcelain").stdout.strip()

    if ahead == 0:
        say("the remote is simply ahead: a fast-forward, no merge commit.")
        if args.check:
            return 0
        if dirty:
            sys.exit("uncommitted changes in the way - commit them (task commit) or `git stash`, then run this again")
        git("merge", "--ff-only", upstream)
        say(f"done: {branch} is at {git('rev-parse', '--short', 'HEAD').stdout.strip()}")
        return 0

    # both sides moved: try the merge in memory before touching anything
    trial = git("merge-tree", "--write-tree", "--name-only", "--no-messages", branch, upstream, check=False)
    conflicts = [name for name in trial.stdout.splitlines()[1:] if name.strip()] if trial.returncode == 1 else []
    if trial.returncode not in (0, 1):
        sys.exit(f"could not try the merge:\n{trial.stderr.strip()}")
    by_hand = [name for name in conflicts if name not in REGENERATED]
    if conflicts:
        say(f"the merge conflicts in {len(conflicts)} file(s):")
        for name in conflicts:
            say(f"  {name}" + ("   (settled automatically: remote side, then re-locked)" if name in REGENERATED else ""))
    else:
        say("the merge is clean: no file was changed on both sides in the same place.")
    if args.check:
        return 1 if by_hand else 0
    if dirty:
        sys.exit("uncommitted changes in the way - commit them (task commit) or `git stash`, then run this again")

    before = git("rev-parse", "--short", "HEAD").stdout.strip()
    merged = git("merge", "--no-edit", upstream, check=False)
    if merged.returncode != 0:
        for name in conflicts:
            if name in REGENERATED:
                git("checkout", "--theirs", "--", name)
                git("add", "--", name)
        if by_hand:
            say()
            say("merge started; these files need your decision (look for <<<<<<< ======= >>>>>>>):")
            for name in by_hand:
                say(f"  {name}")
            say()
            say("then:    git add <files>  &&  git merge --continue  &&  uv lock  &&  task test")
            say("give up: git merge --abort     (back to exactly where you were)")
            return 1
        git("commit", "--no-edit")
    say(f"merged {upstream} into {branch}: {git('rev-parse', '--short', 'HEAD').stdout.strip()}")

    if Path("pyproject.toml").exists() and Path("uv.lock").exists() and subprocess.run(
            ["uv", "lock", "--check"], capture_output=True, check=False).returncode != 0:
        say("uv.lock no longer matches pyproject.toml after the merge: re-locking ...")
        subprocess.run(["uv", "lock", "--quiet"], check=True)
        say("uv.lock changed - commit it (task commit) before pushing.")
    say()
    say("next:    task test   then   git push")
    say(f"undo:    git reset --hard {before}     (only before pushing)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
