# Commit writer

> A commit per changed file, each message written by a local model.

## What it is

`gitrecon commit-files` looks at what differs from the last commit, puts the files in an
order, and has a model fill in a commit form for each - the same form `task commit` asks a
person: type, scope, subject, body, breaking change, footer. Commitizen turns the answers
into the message, so it passes the same check.

- **A plan first.** Without `--apply` nothing is committed: you see file, message, and
  whether the model or the fallback wrote it.
- **Order.** Files other changed files import come first (the import graph of
  [[captorlex]]), then code, configuration, tests, prose.
- **Fallback.** When the model's answer cannot be used, the message is written from the
  path (`docs: update README.md`); `--no-model` does that for everything.
- **`--apply`.** One commit per file, hooks running for each; the routines that act on the
  whole tree (stage everything, push) are switched off for the series; it stops at the first
  commit a hook refuses and leaves the rest untouched. It never pushes.

## Where

`gitrecon.llm.commit_writer` (`changed_files`, `order_changes`, `commit_form`,
`build_message`, `plan_commits`, `apply_plan`). CLI: `gitrecon commit-files [PATH] [--model M]
[--no-model] [--limit N] [--apply]`; `task commit:files`.

## Relations

Uses the [[llm]] interface; writes the Conventional Commits that [[humanish]] reads back.
