# Routine

> A step done the same way around every commit, switched on in `.husky/bos.config.json`.

## What it is

`auto_gitaddall_before_commit` stages everything; `auto_push_after_commit` pushes the branch after the commit (never `master`, a detached HEAD or mid-rebase commits).

## Where

`.husky/bos/routines.py`; `task hooks:routines` shows which are on.

## Relations

Runs inside the git hooks of the [[craft-loop]].
