# Committing and releasing

gitrecon follows the BOS [[craft-loop]].

## Committing

The shortest way, with nothing to write:

```sh
task save          # one commit of everything that changed; the message is written for you
```

The message is made from the list of changed files (`chore: save 12 files (src 5, docs 4,
tests 3)`, the files in the body). Hooks run as for any commit, and autopush pushes it.
`gitrecon commit-files . --single` shows the message without committing.

To word a commit yourself:

```sh
task commit        # commitizen asks, writes a Conventional Commit
```

On every commit the hooks:

- stage everything ([[routine]] `auto_gitaddall_before_commit`),
- sync `metadata.json` into the manifests and lockfiles ([[metadata-sync]]), check them,
  run the tests,
- reject messages that are not Conventional Commits,
- push the branch ([[routine]] `auto_push_after_commit`; never `master`).

Work on `development`, or on `feature/<name>` / `fix/<name>` branches.

## What commitizen is, in short

A commit message here is a small form, and commitizen (`cz`) is the tool that asks it,
checks it and later reads it back:

```
<type>(<scope>): <subject>          feat(cli): add the score command

<body>                              why, in a sentence or two

<footer>                            BREAKING CHANGE: ... / Refs #12
```

| Part | Meaning | Rule |
| --- | --- | --- |
| type | what kind of change | one of `feat fix docs style refactor perf test build ci` (`chore`, `bump`, `revert` also pass the check) |
| scope | which part of the project | optional, one word - **no spaces**, which is why long scopes here are written-with-dashes |
| subject | what changed | imperative, lower case, no full stop |
| body, footer | why; issues; `BREAKING CHANGE: ...` | optional |

What it is for: the *type* decides the next version when a release is cut - `fix`, `refactor`,
`perf` raise the patch, `feat` the minor, a breaking change the major (this project's loop has
its own, calmer policy in `.github/bos.config.json`) - and the changelog is built from the
subjects.

| Command | Does |
| --- | --- |
| `task commit` (`cz commit`) | asks the form, writes the commit |
| `cz check --message "feat: x"` | says whether a message passes (the `commit-msg` hook does this) |
| `cz commit --dry-run --write-message-to-file FILE` | asks the form and only writes the message to a file |
| `cz bump` | next version, changelog, tag - the loop does this, not you |
| `cz info`, `cz example`, `cz schema` | the explanations you found |

The form is also reachable from code - this is what the commit writer below builds on:

```python
from commitizen import factory
from commitizen.config import read_cfg

cz = factory.committer_factory(read_cfg())
cz.questions()            # the form: prefix, scope, subject, body, is_breaking_change, footer
cz.message({"prefix": "feat", "scope": "cli", "subject": "add x", "body": "", "is_breaking_change": False, "footer": ""})
cz.schema_pattern()       # the regular expression `cz check` uses
```

## A commit per file

```sh
task commit:files                       # a plan: every changed file with a message; commits nothing
task commit:files -- --apply            # make the commits, one per file
task commit:files -- --limit 5
```

The messages come from a *handler* ([[commit-writer]]). The only one today is `path`: plain
messages from where a file lives and what happened to it (`docs: update README.md`,
`test(tests): add test_core.py`). Better handlers are written as functions and chosen with
`--handler NAME`.

> **Remember!** `--apply` does not push. With autopush on, the next ordinary commit pushes
> the series; or `git push`.

## When the push is refused: merging the remote in

Every release ends with `master` merged back into `development` on GitHub (the version bump
and the changelog). A commit made here before pulling that makes the two versions of
`development` diverge, and the push after the commit is refused.

```sh
task merge:check      # look only: how far apart, would it conflict, in which files
task merge:remote     # do it: fast-forward, or a merge commit when both sides have commits
task test && git push
```

`merge:remote` fetches, tries the merge in memory first, refuses to work over uncommitted
changes, and never pushes or rewrites commits. What it prints at the end is the way back:
`git reset --hard <commit>` (only before pushing).

If both sides changed the same lines it stops with the files listed. Open each, keep what is
right between the `<<<<<<<`, `=======`, `>>>>>>>` marks, then:

```sh
git add <files> && git merge --continue && uv lock && task test
git merge --abort        # or give up: back to exactly where you were
```

Conflicts in `uv.lock` and `package-lock.json` are settled for you (remote side, then
re-locked). The usual real conflict is the `version` line of `pyproject.toml`,
`metadata.json`, `package.json` or `src/gitrecon/__init__.py`: keep the remote (higher) one.

> **Remember!** To avoid it: `task merge:remote` before starting work after a release went
> through the loop.

## Commits made on GitHub's pages

A commit made in the browser carries GitHub's wording, not a Conventional Commit, and then
fails the message check of every pull request it travels in. Saving issue templates from
the repository settings does that ("Update issue templates"); that one wording is allowed
(`allowed_prefixes` in `pyproject.toml`). For anything else edited in the browser, write the
message yourself: `docs: ...`, `ci: ...`.

## The loop

```
feature/*, fix/*  →  development  →  revision  →  testing  →  releasing  →  master
                          ↑                                                    │
                          └────────────────── back-merge ──────────────────────┘
       any stage  →  rejection  →  development
```

Pull requests to the next stage open automatically; `task gh:loop` shows which steps merge
on their own. Checks: commit messages, metadata sync, tests; apart from them GitGuardian scans
every push for secrets (`.github/workflows/gitguardian.yaml`, secret `GITGUARDIAN_API_KEY`).

A loop pull request shows two runs of the checks: the one the loop starts itself (the one
that counts and merges), and one GitHub creates for the pull request event. The second
belongs to the bot, waits for approval ("action required") or ends without jobs - it can be
ignored.

## Releases

Every pass through `master`: version bump (patch, minor on a breaking change), changelog,
`vX.Y.Z` tag, wheel and sdist attached to a GitHub Release, back-merge PR into
`development`. Don't bump or tag by hand.

`AUTHORS` is refreshed in the middle of a release: after `testing` was merged into
`releasing` and before the pull request to `master` is opened, the loop runs
`gitrecon contributors --ignorelist --format authors`, and commits the file to `releasing`
when it changed (`scripts/delegated/workflow-gh/release/authors.sh`). Who is left out is in
`resources/ignorelist.txt`.
