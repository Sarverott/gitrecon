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

## The loop

```
feature/*, fix/*  →  development  →  revision  →  testing  →  releasing  →  master
                          ↑                                                    │
                          └────────────────── back-merge ──────────────────────┘
       any stage  →  rejection  →  development
```

Pull requests to the next stage open automatically; `task gh:loop` shows which steps merge
on their own. Checks: commit messages, metadata sync, tests.

## Releases

Every pass through `master`: version bump (patch, minor on a breaking change), changelog,
`vX.Y.Z` tag, wheel and sdist attached to a GitHub Release, back-merge PR into
`development`. Don't bump or tag by hand.
