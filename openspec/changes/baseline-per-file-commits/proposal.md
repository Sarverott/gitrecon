# Proposal

## Why

gitrecon is moving its way of working to OpenSpec, and its specs folder is empty: nothing yet
says what the existing code must keep doing. This change records one existing capability -
committing changes one file at a time - as the first spec. It is the capability the next
work will touch (new commit handlers), so its contract is worth having first, and it serves
as the worked example for bringing the other capabilities in.

## What Changes

- No behaviour changes. The per-file commit planner already exists (`gitrecon commit-files`,
  `gitrecon.committing`) and is covered by tests.
- Its observable behaviour is written down as requirements with scenarios.

## Capabilities

### New Capabilities
- `per-file-commits`: planning and making one commit per changed file - the order of files, who writes each message (handlers) and what happens when a handler cannot, the shape every message must have, and what applying a plan may and may not do to the repository.

### Modified Capabilities

## Impact

- New: `openspec/specs/per-file-commits/spec.md` (after archive).
- Code described, not changed: `src/gitrecon/committing/`, the `commit-files` command in
  `src/gitrecon/cli/content.py`, `.husky/bos/routines.py` (`BOS_SKIP_ROUTINES`),
  `tests/test_committing.py`.
