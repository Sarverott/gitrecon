# gitrecon — agent guide

Tool for exploring, recognizing and regularly checking GitHub activity of users,
organizations, repositories and projects. It maps what it finds, concludes labels
for what is happening, keeps the shared map dataset up to date, and drafts
articles and posts from summaries of the data.

## Layout

```
src/gitrecon/
├── main.py         CLI (argparse subcommands) — entry point `gitrecon`
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
├── mapping/        graph — ActivityGraph: entity nodes + evidenced edges
├── analysis/       timeline (windows, cadence), rules (one function per label), labeler
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
- **example**: `examples/push_map.py` runs the whole map refresh and push via the library.

## Delivery (ported from shakespeare-mobile)

- `metadata.json` is the single source of name/version/description/authors/tags;
  `scripts/sync_metadata.py` copies it into `package.json`, `pyproject.toml`, lockfiles.
- `.husky/` hooks call `.husky/Taskfile.yml`; routines switched in `.husky/bos.config.json`.
- `.github/bos.config.json` + `.github/bos/flow.py` drive the branch loop
  `development → revision → testing → releasing → master → development`.
- Multi-line CI steps live in `scripts/delegated/workflow-gh/<workflow>/<step>.sh`.

## Working rules

- Python ≥ 3.12, managed with `uv`. Run tests: `task test`.
- Tests are offline; `tests/conftest.py` blocks real HTTP. Use `FakeSession`.
- Work on `development` (or `feature/*`, `fix/*`), never directly on `master`.
  Commit messages follow Conventional Commits (`task commit`).
- Legacy notebooks (`docs/*.ipynb`, `datasets/*.ipynb`) and their marimo
  conversions (`tools/*.py`) are kept as originals; the code lives in `src/gitrecon/`.
  `tests/fixtures/taskfile-llms.*` pins the RAT output to the original notebook.
- Data goes to `data/` and the map to `datasets/imperialmap/` (both git-ignored).
- Pushing the map to Hugging Face and publishing posts are outward-facing: confirm first.
- Respect GitHub rate limits and the Acceptable Use Policies; do not build profiles
  of private individuals.
