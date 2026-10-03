# gitrecon

Exploring, recognizing and listening to GitHub activity of users, organizations,
repositories and projects: collect events into a raw buffer, map who touches
what, and conclude labels for what is happening.

## Install

```sh
task install              # uv sync + npm install (git hooks)
export GITHUB_TOKEN=...   # optional; falls back to `gh auth token`, else 60 requests/hour
export OLLAMA_MODEL=llama3   # digest (local Ollama, OLLAMA_HOST)
export XAI_API_KEY=...       # posts (XAI_MODEL, default grok-4)
```

Secrets can also live in a dotenv file: `GITRECON_ENV_FILE`, the project `.env`,
or (for now) `__WORKSHOP/forge/.env` - existing variables always win.
LLM interfaces (Ollama, OpenAI-compatible enterprise endpoints) are on hold: TODO.

Or in a container: `task docker:run -- stars sarverott` (see `docs/guides/installation.md`).

## Usage

The quickest start: `task menu` (or `uv run gitrecon`) - a full-screen menu where every command,
task, example and manual is picked with the arrows and Enter.

```sh
# collect
gitrecon events public              # one poll of the public event stream
gitrecon events org:github --watch  # keep listening (ETag + X-Poll-Interval)
gitrecon events repo:owner/name
gitrecon gists                      # newest public gists
gitrecon gists --user octocat
gitrecon archive 2026-10-01-0 2026-10-01-23   # GH Archive hours (UTC), streamed to disk

gitrecon stars sarverott            # every repository a user has starred (--save keeps them)
gitrecon stars sarverott --urls     # ...just their addresses, one per line
gitrecon stars sarverott --json > sarverott-stars.json      # ...or all of it as a JSON file
gitrecon gist-catalog sarverott     # every gist: files, stars, comments, forks, commits, size
gitrecon repos sarverott --no-forks # own repositories; orgs sarverott; org-repos ORG
gitrecon repo-clone sarverott ~/__WORKSHOP/forge/sarverott/repos --dry-run   # also gist-clone, org-clone
gitrecon links ..                   # harvest data source links from gist clones in ..
gitrecon links .. --kind feed --save

# more sources
gitrecon feeds --items              # RSS/Atom/RDF feeds from the link catalog (or give URLs); --save
gitrecon rfc --search quantum ssh   # RFC Editor index; --number 2026, --save
gitrecon blog --dump                # Apokryf blog articles as markdown (any blog URL); --save

# the map dataset (Hugging Face Apokryf/minimap-of-uce -> datasets/imperialmap)
gitrecon atlas pull
gitrecon atlas update               # gist links -> dnstrees, GitHub /meta -> ip-address-records
gitrecon atlas update --stars sarverott   # + user-namespace: owners of starred repos
gitrecon atlas status
gitrecon atlas push -m "message"    # HF_TOKEN from .env; --pr to open a Hub PR
task map:refresh && task map:push -- -m "message"          # the whole refresh + push

# content: summarize locally, then write drafts
gitrecon digest stars:sarverott     # Ollama map-reduce; also labels | links | file:PATH
gitrecon posts data/digests/<file>.md   # xAI: SEO article, tweet thread, LinkedIn, Mastodon

# for programs: most commands take --json (only data on stdout) or --urls (only addresses)
gitrecon stars sarverott --json | jq '.[].url'
gitrecon events org:github --watch --json      # JSON Lines, live
gitrecon label --name star-burst --urls

# look
gitrecon status                     # what is in the raw buffer
gitrecon map                        # graph summary: nodes, relations, hubs
gitrecon map --node user:octocat    # neighbors of one entity
gitrecon label                      # labels with confidence and evidence

# text experiments
gitrecon text toc|tokens|rat [URL]
```

Data lands in `./data` (override with `GITRECON_DATA`) as gzip JSONL partitioned
by source and UTC hour.

## Labels

| Label | Target | Meaning |
|---|---|---|
| `declared-bot` | user | `[bot]` account or `type: Bot` |
| `burst` | user | many events within one window |
| `bot-like-cadence` | user | evenly spaced events (low gap variation) |
| `push-flood` | user | many commits pushed within one window |
| `repo-spree` | user | many repositories created within one window |
| `mass-forker` | user | many forks made within one window |
| `fork-wave` | repo | many forks of one repo within one window |
| `star-burst` | repo | many stars within one window |
| `mass-gist-drop` | user | many gists created within one window |

Thresholds live in `gitrecon.analysis.Thresholds`.

## Environment

Services around gitrecon - databases, gitea, ollama, n8n, traefik, runners and more - are
docker compose files in `services/<group>/`, behind one gateway (traefik: every web service
is `<name>.gr.rs-tech.online`, or `<name>.localhost:8880` on the host; a WireGuard bubble for the rest),
started with their dependencies:
`task services:list`, `task services:up -- gitea n8n`. Their data lives in
`datasets/_dockdrives/<volume>` (`task services:drives`, `task services:backup`); see
`docs/guides/environment.md`.

## Examples and documentation

- `examples/<title>/` - runnable Jupyter notebooks with concrete calls (`task examples:list`,
  `task examples:launch`, `task examples:marimo`); see [examples/README.md](examples/README.md)
- `docs/` - guides and a glossary (an Obsidian vault, built with MkDocs on Read the Docs):
  `task manuals` reads them in the terminal, `task docs:serve` previews the site
- `task help` lists every task

## Development

```sh
task test
task commit
```

Work goes through the BOS craft loop (`development → revision → testing →
releasing → master`), with Conventional Commits, metadata sync and automated
releases. See [CONTRIBUTING](.github/CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).
