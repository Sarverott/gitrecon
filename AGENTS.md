# gitrecon — agent guide

Tool for exploring, recognizing and regularly checking GitHub activity of users,
organizations, repositories and projects. It maps what it finds, concludes labels
for what is happening, keeps the shared map dataset up to date, and drafts
articles and posts from summaries of the data.

## Layout

```
src/gitrecon/
├── main.py         entry point `gitrecon` → gitrecon.cli
├── cli/            commands by area: collect, analyze, atlas, content; output (text|--json|--urls)
├── tui/            interactive menu (rich): app, widgets (Selector, Viewer), commands (CLI → forms),
│                   taskfiles (task --list-all --json + YAML), manuals, keys, theme
├── config.py       paths anchored at the project root; GITRECON_DATA, GITRECON_DATASETS,
│                   GITHUB_TOKEN / GH_TOKEN (falls back to `gh auth token`), dotenv loading
│                   (TODO: forge-level .env is temporary)
├── models/         one domain class per file: User, Organization, Repository, Gist,
│                   Project, Event, Star, Label, RFC, FeedItem, BlogArticle
│                   (+ base.Entity, records.from_record)
├── sources/        github_api (REST client: ETag, X-Poll-Interval, rate limit),
│                   events (feed poller), gists, stars, gharchive, links (gist link harvest),
│                   feeds (RSS/Atom/RDF), rfc_index (RFC Editor index), blog (articles + feed discovery)
├── storage/        rawbuffer — append-only gzip JSONL, data/raw/<source>/<day>/<HH>.json.gz
├── mapping/        graph — ActivityGraph: entity nodes + evidenced edges; network — relations around a
│                   user (member_of, owned_by, fork_of); render — Mermaid (owners | repos), DOT, JSON;
│                   gitgraph — history across branches as a Mermaid gitGraph;
│                   score — the same history as guitar tab, ABC, MIDI
├── analysis/       timeline (windows, cadence), rules (one function per label), labeler
├── code/           what repositories are made of: languages, lexical (Lark lexers), pyast, frameworks,
│                   analyze — all driven by resources/
├── openapi.py      the commands and tasks as an OpenAPI document (generated contract)
├── committing.py   `save`: one commit of everything, the message written from the changed paths
├── humanish/       controlled sentences by grammar: commits (forms, types, labels), requirements
├── translate/      argos — offline translation (translate extra)
├── atlas/          the map dataset: layout (paths), deterministic updates (update),
│                   user-namespace identities (namespace)
├── hub/            huggingface — MapDataset pull/push of Apokryf/minimap-of-uce
├── digest/         llm (Ollama + xAI clients), summarize (map-reduce), inputs, posts
└── text/           markdown, tokenizer, a12y glossary, RAT builder, Lark JSON grammar
```

## Pipelines

- **recon**: `sources` → `storage.RawBuffer` (never rewritten) → `mapping` / `analysis`
  (always rebuilt from the raw buffer). New label = new function in `analysis/rules.py`
  added to the matching `*_RULES` list, threshold in `Thresholds`, test in `tests/`.
- **map**: `atlas pull` → `links --save` (catalog from gist clones in `..`) →
  `atlas update` (writes `datasets/imperialmap`, idempotent) → `atlas push -m …`.
- **content**: `digest <input>` (Ollama, local, map-reduce over any size) →
  `posts <digest.md>` (xAI) → drafts in `data/posts/`. Nothing is published automatically.
  TODO(llm-interfaces): Ollama / OpenAI-compatible enterprise endpoints are on hold.
- **user-namespace**: follows `datasets/imperialmap/user-namespace/README.md` —
  `NS/<a12y(user)>/<a12y(platform)>/<md5("user@platform\n")>.json` + `index.json`.
  Only public platform accounts are added automatically; no e-mail harvesting.
- **examples**: `examples/<title>/notebook.ipynb` or `examples/<title>/<NN-chapter>.ipynb`,
  each folder with `README.md` and `Taskfile.yml` (includes `examples/Taskfile.notebooks.yml`:
  launch, run, marimo, clean). Notebooks are committed without outputs; `.out/` and `marimo/`
  are generated. Anything publishing (map push) stays behind an explicit flag.
- **devlog**: `docs/devlog/scrapnote-<UNIXUSAT>.md` (epoch ms, `node -e 'console.log(Date.now())'`) -
  notes of a working round, not sorted yet; add them to the `Devlog` nav of `mkdocs.yml`.
- **docs**: `docs/` is an Obsidian vault and a MkDocs sub-project (own `pyproject.toml`, built
  by Read the Docs from `.readthedocs.yaml`): `glossary/` one page per element, `guides/`.
  New element → glossary page + `glossary/README.md` + `mkdocs.yml` nav. `task docs:build`
  must pass (`--strict`). `task manuals` reads the docs in the terminal.

## Delivery (ported from shakespeare-mobile)

- `metadata.json` is the single source of name/version/description/authors/tags;
  `scripts/sync_metadata.py` copies it into `package.json`, `pyproject.toml`, lockfiles.
- `.husky/` hooks call `.husky/Taskfile.yml`; routines switched in `.husky/bos.config.json`.
- `.github/bos.config.json` + `.github/bos/flow.py` drive the branch loop
  `development → revision → testing → releasing → master → development`.
- Multi-line CI steps live in `scripts/delegated/workflow-gh/<workflow>/<step>.sh`.

## Container

`Dockerfile` (python:3.12-slim - the `llm` extra's onnxruntime has no Alpine build; two stages, the
venv and `resources/` are copied, git installed; `EXTRAS` build arg, hub extra by default) + `compose.yaml` (service `gitrecon` for one-off commands, `listen`
under the `listen` profile). `.dockerignore` is an allow-list: pyproject, lock, README, src.
Runtime-only dependencies stay minimal - anything not imported by `src/` belongs in a group.

## Reading code: PeekerLex and CaptorLex

- **PeekerLex** = the quick reading (`gitrecon.code`: lexers, tables, manifests).
  **CaptorLex** = the deep reading (structure -> relations -> meaning); step 1 exists:
  `gitrecon.code.structure` (tree-sitter, `code` extra, `analyze --deep`) and `pyast`.
  Step 2 inside one repository: `gitrecon.code.imports` (Python by `ast`, others by
  `resources/imports.yml`; networkx for cycles). Second circle, between an owner's repositories:
  `gitrecon.code.relations` - submodules first, then dependencies (the user's order of
  strength); then all known public repositories; URLs in code, then in text, last. The user's names: use them.
- Results are kept by default in both the raw buffer (`data/raw/analysis/`) and the map
  (`data-heuristicality/code-analysis/<platform>/<owner>/<repo>.json`, `gitrecon.code.store`);
  `analyze --no-save`, clone commands `--no-analysis`. Only repositories GitHub shows public go
  to the map (`store.not_public`); `--map-priv-repos` writes the others too.
- No Rattish grammar here: it belongs to the rattish project (`forge/rattish/rattish/TODO.md`).

## CI facts

- CI runs the tests on the runner's system Python (3.12.3 today), older than the local one:
  argparse there rejects words after options for `nargs="*"` positionals - commands with such
  an argument set `rest=` in their parser defaults (`cli._late_positionals`). Check with
  `uv run --python 3.12.3 --isolated --no-default-groups --group test pytest`.
- `cz check` runs over every commit of a PR: a browser commit with GitHub's wording blocks
  the whole loop (`allowed_prefixes` in pyproject.toml holds the one exception).
- Issue templates (`.github/ISSUE_TEMPLATE/`) use only labels that exist in the repository.

## Merging the remote in

- `task merge:check` / `task merge:remote` (`scripts/merge_remote.py`): the procedure for a
  diverged branch (the loop back-merges master into development on GitHub). Trial merge in
  memory, no work over a dirty tree, never pushes, prints the undo command. Lockfile conflicts
  take the remote side and re-lock; version lines: keep the remote one.

## The interface as data

- `resources/openapi/gitrecon.openapi.yaml` is generated (`task openapi`, `gitrecon.openapi`)
  from the argparse parser and the Taskfile: after adding or changing a command or its
  options, run `task openapi` - `tests/test_openapi.py` fails otherwise. Never edit it by hand.
  It is a contract for a future GUI; there is no HTTP server.
- `resources/llms/` holds model-tooling configuration only (`litellm.yaml`). gitrecon does not
  run a model server, pull models or start agents; the `services/` environment was removed
  and belongs in a separate project.

## Saving

- `gitrecon.committing` is one small module: `changed_files`, `save_message` (a Conventional
  Commit written from the changed paths), `save`. `task save` = `gitrecon save .`. The owner
  runs it; do not commit for them.
- Importing commitizen disables existing loggers - nothing in `src/` imports it any more; keep it so.

## Contributors and the ignorelist

- `gitrecon.mapping.contributors`: people from the git log (mailmap honoured; same address or
  same name = one person). `--ignorelist [FILE]` (default `resources/ignorelist.txt`) on
  `contributors` and `score`. Ignorelist patterns use only `*` and `?` - `[bot]` is literal.
- Mermaid pies come from `contributors.pie()` (contributors, languages, kinds of outward ties).
- `gitrecon relations REPOSITORY` = outward ties in the user's order of firmness: fork, (local),
  registry, custom-registry, git, http; stars after them (not built), links last.
- `gitrecon.text.mathtext` (math extra): LaTeX -> SymPy through SymPy's Lark parser; small on purpose.

## Humanish and translation

- `gitrecon.humanish`: controlled sentences by grammar (`resources/grammars/humanish/`,
  meanings in `resources/humanish.yml`) - commit messages (`commits`), requirement keywords
  (`requirements`). Levels 2-3 (normative text, free text) are other projects' ground.
- With Lark's Earley parser a terminal matches one way only: alternatives that share a prefix
  (`BREAKING CHANGE` vs a word) need separate terminals.
- `gitrecon.translate.argos`: Argos Translate behind `_argos()` (lazy import; tests fake it).

## Dependencies

- Core stays light; heavy libraries live in extras: `hub`, `llm` (chromadb, langchain, litellm,
  nanobot, ollama, openai), `net` (paramiko, scapy), `code` (tree-sitter), `translate` (argostranslate; brings torch),
  `all`. Import them lazily inside the
  function that needs them. Coming groups (social media, translation, media generation) get
  their own extras the same way.

## Resources (resources/)

- Knowledge is data: `languages.yml` (extensions, families, keywords), `frameworks.yml`
  (manifests, packages, marker files), `grammars/` (Lark: `json.lark`, `lexical/<family>.lark`
  with terminals COMMENT, STRING, NUMBER, NAME, OTHER). Read through
  `gitrecon.config.resource()`; `GITRECON_RESOURCES` overrides the folder.
- New language / framework / family = an edit there, not code; `tests/test_code.py` checks the
  tables against each other. In YAML keyword lists quote `true`, `false`, `null`, `yes`, `no`, `on`.
- `resources/locales/` and `resources/rss.json` are the user's, in progress: leave them.
- Mermaid can be checked for real: `@mermaid-js/mermaid-cli` with a Chrome from
  `~/.cache/puppeteer` (the snap Chromium cannot read /tmp).

## Cloning defaults

Clone commands take an optional path; without one, clones go to the active workshop's forge
(`gitrecon.config.forge_dir()`, `GITRECON_FORGE` overrides): `<forge>/<user>/` for
`repo-clone`, `<forge>/<org>/` for `org-clone`, `<forge>/<user>/my-gists` for `gist-clone`
(`sources.cloning.default_clone_path`, which reuses an existing folder of another letter case).

## Output contract (CLI)

- Every listing command takes `--json` and, when items have web pages, `--urls`
  (`add_output_flags()`); print through `Output` (`listing`, `stream`, `result`, `note`).
- Machine modes: stdout holds only data (JSON list / object / JSON Lines for streams, or
  one URL per line); notes, progress and summaries go to stderr via `out.note()`.
- Item shapes come from models' `to_json()`; addresses from `html_url` (`url_for_key()` for
  bare keys). New model → `html_url` + `to_json()`; new command → both flags + a test in
  `tests/test_cli_output.py`; document shapes in `docs/guides/integration.md`.

## Menu (gitrecon.tui)

- Nothing is listed by hand: commands come from `gitrecon.cli.build_parser()`, tasks from
  `task --list-all --json` + their YAML. Give every new command a `help`, every option a
  `help`, every task a `desc`; write `e.g. task NAME -- ARGS` (or `NAME VAR=value`) in a
  task's desc - the menu uses it as the default input.
- Widgets keep state apart from drawing (`handle(key)` / `render()` / `run()`): test the
  state, not the terminal (`tests/test_tui.py`).
- The menu must degrade without Task, docs or examples (it runs in the container too).

## OpenSpec (being adopted)

- `openspec/` holds specs (`specs/<capability>/spec.md`: what must hold) and changes
  (`changes/<name>/`: proposal, spec delta, design, tasks). CLI: `openspec list`, `show`,
  `status --change NAME`, `instructions ARTIFACT --change NAME`, `validate --all --strict`.
- Project rules for OpenSpec artifacts are in `openspec/config.yaml` (context, per-artifact
  rules). Keep them in step with this file.
- An existing capability gets its spec when a change first touches it: a `baseline-<name>`
  change that records current behaviour, then the real change on top. Archiving a change is the owner's call.
- Generated files (`.github/agents`, `.github/prompts/opsx-*`, `.github/skills/openspec-*`,
  `copilot-setup-steps.yml`) come from `openspec init` / `openspec update`: edit sparingly.

## Working rules

- Python ≥ 3.12, managed with `uv`. Run tests: `task test`.
- Tests are offline; `tests/conftest.py` blocks real HTTP. Use `FakeSession`.
- Work on `development` (or `feature/*`, `fix/*`), never directly on `master`.
  Commit messages follow Conventional Commits (`task commit`).
- The first notebooks (`docs/*.ipynb`, `datasets/setups.ipynb`, `tools/*.py`, root `main.py`)
  were fully assimilated into `src/gitrecon/` and `examples/`, then removed (see git history).
  `tests/fixtures/taskfile-llms.*` still pins the RAT output to the first notebook.
- Data goes to `data/` and the map to `datasets/imperialmap/` (both git-ignored).
- Pushing the map to Hugging Face and publishing posts are outward-facing: confirm first.
- Respect GitHub rate limits and the Acceptable Use Policies; do not build profiles
  of private individuals.

