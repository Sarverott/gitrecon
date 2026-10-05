# Commit writer

> A commit per changed file; who writes the messages is a handler.

## What it is

`gitrecon commit-files` looks at what differs from the last commit, puts the files in an
order, and asks a **handler** to answer the commit form for each - the form `task commit`
asks a person: type, scope, subject, body, breaking change, footer. The answers become a
Conventional Commit.

- **A plan first.** Without `--apply` nothing is committed.
- **Order.** Files other changed files import come first, then code, configuration, tests, prose.
- **Handlers.** A handler is a function `handler(context) -> answers`. The context carries
  the change, the facts gitrecon knows about the file (language, lines changed, which files
  it uses, how many use it), its diff, and the form's fields. Returning `None`, raising, or
  answering something that is not a valid message hands the file to the `path` handler, so
  a plan is always complete - and says so in a note.
- **The `path` handler** is the only one today: the type from where the file lives
  (`docs`, `test`, `ci`, `build`, else `chore`), the subject from what happened
  (`add`, `update`, `remove`, `rename` + the file name).
- **`--apply`.** One commit per file, hooks running for each; the routines that act on the
  whole tree (stage everything, push) are switched off for the series; it stops at the first
  commit a hook refuses and leaves the rest untouched. It never pushes.

## Writing a handler

```python
from gitrecon.committing import ChangeContext, register

@register("mine")                       # choosable as: gitrecon commit-files --handler mine
def mine(context: ChangeContext) -> dict | None:
    if context.facts.get("language") != "Python":
        return None                     # pass: the path handler answers
    return {"prefix": "refactor", "scope": "core", "subject": f"tidy {context.change.path}"}
```

`context.change` (path, status, old_path), `context.facts`, `context.diff`,
`context.form` (the fields with their choices), `context.position` / `context.total`.

## Where

`gitrecon.committing`: `changes` (what changed, facts, order), `form` (the form, the
message), `handlers` (the registry, the context, `path_handler`), `plan` (`plan_commits`,
`apply_plan`). CLI: `gitrecon commit-files [PATH] [--handler NAME] [--limit N] [--apply]`;
`task commit:files`.

## Relations

Writes the Conventional Commits that [[humanish]] reads back; orders by the import graph of
[[captorlex]]. A model-backed handler was tried and is parked ([[llm]]).
