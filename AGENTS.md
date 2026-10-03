# gitrecon — agent guide

Tool for exploring, recognizing and regularly checking GitHub activity of users,
organizations, repositories and projects. It maps what it finds and concludes
labels for what is happening.

## Layout

```
src/gitrecon/
├── main.py         CLI (argparse subcommands) — entry point `gitrecon`
├── config.py       env config: GITRECON_DATA, GITHUB_TOKEN / GH_TOKEN
├── models/         one domain class per file: User, Organization, Repository,
│                   Gist, Project, Event, Label (+ base.Entity, records.from_record)
├── sources/        github_api (REST client: ETag, X-Poll-Interval, rate limit),
│                   events (feed poller), gists, gharchive (hourly dumps)
├── storage/        rawbuffer — append-only gzip JSONL, data/raw/<source>/<day>/<HH>.json.gz
├── mapping/        graph — ActivityGraph: entity nodes + evidenced edges
├── analysis/       timeline (windows, cadence), rules (one function per label), labeler
├── text/           markdown, tokenizer, a12y glossary, RAT builder, Lark JSON grammar
└── hub/            Hugging Face dataset sync (dev dependency, lazy import)
```

## Pipeline

`sources` → `storage.RawBuffer` (never rewritten) → `mapping` / `analysis` (always
rebuilt from the raw buffer). New label = new function in `analysis/rules.py`
added to the matching `*_RULES` list, threshold in `Thresholds`, test in
`tests/test_pipeline.py`.

## Working rules

- Python ≥ 3.12, managed with `uv`. Run tests: `task test` (or `uv run pytest`).
- Tests are offline. Never hit the network from `tests/`.
- Work on `developement`, never directly on `master`.
- Legacy notebooks (`docs/*.ipynb`, `datasets/*.ipynb`) and their marimo
  conversions (`tools/*.py`) are kept as originals; the code lives in `src/gitrecon/`.
  `tests/fixtures/taskfile-llms.*` pins the RAT output to the original notebook.
- Data goes to `data/` (git-ignored). Respect GitHub rate limits and the Acceptable
  Use Policies; do not build profiles of private individuals.
