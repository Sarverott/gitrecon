# Design

## Context

The capability exists. It was built first around a local language model, then separated from
it: the model code is parked (`src/gitrecon/llm/`, commented out) and what remains is a
planner with a handler interface. This document records the decisions already taken, so the
spec has its reasons next to it.

## Goals / Non-Goals

**Goals:**
- Capture the current behaviour of `gitrecon commit-files` as a contract.
- Keep the way messages are written replaceable without touching the planner.

**Non-Goals:**
- Any new handler (a model, rules, a person filling a form) - each is its own change.
- Grouping several files into one commit.
- Changing what the commit hooks do.

## Decisions

- **Four parts** - `changes` (what changed, facts, order), `form` (the commit form and the
  message), `handlers` (registry, context, the path handler), `plan` (planning and applying).
  New ways of writing messages are new handlers; the planner does not grow.
- **The form is commitizen's own.** A handler answers the same questions `task commit` asks
  a person, and commitizen builds the message when it is installed; without it the same
  shape is built by hand. One check (`cz check`) then covers people and handlers alike.
- **Fallback instead of failure.** A handler may be weak or unavailable; a plan that stops
  halfway is worse than a plain message with a note. Hence the path handler behind every
  other handler.
- **Order from the import graph**, including untracked files, because new files are part of
  what is being committed. Alternative considered: order by path only - loses the "each
  commit stands on the previous" property.
- **`BOS_SKIP_ROUTINES=add-all,push` during apply.** The hooks stay on (sync, tests, message
  check), but "stage everything" would put the whole tree into the first commit and
  "push after commit" would push once per file.
- **`git commit --only -- <file>`** so a commit holds one file whatever else is staged.

## Risks / Trade-offs

- The pre-commit hook stages manifests and lockfiles; pending changes there ride along with
  the first commit of a series. Accepted for now, noted in the docs.
- The path handler's messages say little (`chore(cli): update content.py`). That is its
  job: to be a floor, not a goal.
- Importing commitizen switches off existing loggers; the form module switches them back on.
  If commitizen changes how it configures logging, that guard needs another look.
