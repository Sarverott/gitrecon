# Committing and releasing

gitrecon follows the BOS [[craft-loop]].

## Committing

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
