# Contributing to gitrecon

gitrecon explores, maps and labels GitHub activity of users, organizations,
repositories and projects. By taking part you agree to follow our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Setting up

You need:

- [uv](https://docs.astral.sh/uv/) (Python ≥ 3.12, tests, commitizen, metadata sync)
- [Task](https://taskfile.dev)
- Node.js and npm, only for the git hooks (husky)
- optional: [Ollama](https://ollama.com) for `gitrecon digest`, an `XAI_API_KEY` for `gitrecon posts`,
  and a Hugging Face login (`uv run hf auth login`) to push the map dataset

```sh
git clone https://github.com/Sarverott/gitrecon.git
cd gitrecon && task install
```

`task --list` shows every task. The most used:

| Task | What it does |
| --- | --- |
| `task test` | Offline test suite + metadata sync check |
| `task lint` | Lints workflows (actionlint) and delegated shell scripts (shellcheck) |
| `task recon -- …` | Runs the CLI, e.g. `task recon -- stars sarverott` |
| `task map:refresh` | Pulls the map dataset, harvests gist links, writes findings into it |
| `task gh:loop` | Shows how the craft loop in `.github/bos.config.json` resolves |
| `task commit` | Commits with commitizen |

## Making a change

1. **Branch from `development`** and name the branch `feature/<short-name>` or
   `fix/<short-name>`.
2. **Write in English**: code, comments and documentation. In issues and
   discussions, Polish and English are both welcome.
3. **Keep tests offline.** `tests/conftest.py` fails any test that makes a real
   HTTP request; use `FakeSession` / `FakeResponse` instead.
4. **Commit with `task commit`.** It writes a
   [Conventional Commits](https://www.conventionalcommits.org) message, such as
   `feat(stars): list starred repositories` or `fix: keep etag between polls`.
   These messages build the changelog and decide the next version.
5. **Push your branch.** A pull request into `development` opens automatically.

### What the hooks do

On every commit, husky runs:

- **pre-commit**: copies the shared project info (name, version, description,
  authors, tags) from `metadata.json` into `package.json`, `pyproject.toml` and
  the lockfiles, checks they match, and runs the tests. Edit that info **only in
  `metadata.json`**, and never change the version by hand.
- **commit-msg**: rejects messages that don't follow Conventional Commits.
- **post-commit**: the push routine (below).

**Routines** are switched in `.husky/bos.config.json`; `task hooks:routines` shows them.

- **`auto_gitaddall_before_commit`**: stage everything before committing.
- **`auto_push_after_commit`**: push the branch after each commit (never
  `master`, a detached HEAD, or mid-rebase/merge/cherry-pick commits).

## The craft loop

```
feature/*, fix/*  →  development  →  revision  →  testing  →  releasing  →  master
                          ↑                                                    │
                          └────────────────── back-merge ──────────────────────┘
       any stage  →  rejection  →  development
```

- `master` is the canon. Nobody commits to it directly.
- `.github/bos.config.json` defines the loop: branches, directions, which PRs
  open automatically and which steps merge on their own
  (`python3 .github/bos/flow.py explain`).
- The checks are: commit messages, metadata sync and the unit tests.
- **The workflows stay short.** Every multi-line step lives in
  `scripts/delegated/workflow-gh/<workflow>/<step>.sh` and runs locally too.

## Releases

Every pass through `master` is a release, made by CI:

1. The version is bumped once per loop: patch normally, minor on a breaking
   change (`feat!: …` or a `BREAKING CHANGE:` footer).
2. `metadata.json`, the manifests, `src/gitrecon/__init__.py` and `CHANGELOG.md`
   are updated, then a `bump: …` commit and a `vX.Y.Z` tag go to `master`.
3. The wheel and sdist are built and attached to a GitHub Release.
4. The back-merge PR `master → development` opens.

Don't run `task bump` yourself, and don't push version tags; CI does both.

## Data and responsibility

gitrecon reads public data only. Respect GitHub's rate limits and Acceptable
Use Policies; focus on organizations, repositories and ecosystem patterns, not
on profiling private individuals. Generated posts are drafts: a person reviews
them before anything is published.

Security problems should go privately to **sett@sarverott.com**, not to a public issue.

## License

gitrecon is licensed under [MIT](../LICENSE).
