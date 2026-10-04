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
│                   gitgraph — history across branches as a Mermaid gitGraph
├── analysis/       timeline (windows, cadence), rules (one function per label), labeler
├── code/           what repositories are made of: languages, lexical (Lark lexers), pyast, frameworks,
│                   analyze — all driven by resources/
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

`Dockerfile` (python:3.12-slim - chromadb's onnxruntime has no Alpine build; two stages, the
venv and `resources/` are copied, git installed; `EXTRAS` build arg, hub extra by default) + `compose.yaml` (service `gitrecon` for one-off commands, `listen`
under the `listen` profile). `.dockerignore` is an allow-list: pyproject, lock, README, src.
Runtime-only dependencies stay minimal - anything not imported by `src/` belongs in a group.

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

## Services (services/)

- `services/<group>/<service>.compose.yaml`, one file per service, listed in the group's
  `compose.yaml`; groups listed in `services/compose.yaml`, which the root `compose.yaml`
  includes. Each group describes itself in `NOTE.md` (table: service, image, address, needs).
- Every service has `profiles: [<group>, <service>]`; start through `services/control.py`
  (`task services:up -- …`), which follows `depends_on` across groups. Databases are shared
  (`databases/`); new apps get a database via `POSTGRES_MULTIPLE_DATABASES`.
- Volumes are declared only in `services/volumes.compose.yaml`, each a bind of
  `${REPO_DIR:-${PWD}}/datasets/_dockdrives/<volume>`; service files just mount them by name.
  `control.py up` creates the folders; `drives` checks, `backup` archives (via a container,
  since services own their folders). Engine queries use the docker/podman SDK; compose
  stays the CLI (the SDKs have no compose).
- No published ports (only traefik, wireguard, transmission peers). A web service gets
  traefik labels: `Host(\`<sub>.${DOMAIN:-gr.rs-tech.online}\`) || Host(\`<sub>.localhost\`)`, its
  container port, and `vpn-only@file` for admin tools. Public (tunnels) only with an explicit
  router on entrypoint `public`. Everything else is reached by name inside the network or
  through the WireGuard bubble (dnsmasq). Main domain `gr.rs-tech.online` is persistent.
- Gateway setup lives in `services/networking/config/` (traefik static/dynamic, dnsmasq,
  ngrok); fixed addresses: traefik 172.30.0.10, dnsmasq .53, wireguard .2 (automatic: .128+).
- No `${VAR:?}` (one unset variable would break every compose command); defaults are dev
  passwords; `task services:env` regenerates `services/.env.example`.
- New service → its file, the group's `compose.yaml`, `NOTE.md`, its volumes in
  `volumes.compose.yaml`, its traefik labels, and `task services:env`; check with `docker compose --profile '*' config -q`.
- `app/` (not created yet, on purpose): the web interface, built later by others - do not
  write there. First the environment, the CLI and the terminal interface.

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
