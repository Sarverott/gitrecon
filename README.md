# gitrecon

Exploring, recognizing and listening to GitHub activity of users, organizations,
repositories and projects: collect events into a raw buffer, map who touches
what, and conclude labels for what is happening.

## Install

```sh
uv sync
export GITHUB_TOKEN=...   # optional; without it the API allows 60 requests/hour
```

## Usage

```sh
# collect
gitrecon events public              # one poll of the public event stream
gitrecon events org:github --watch  # keep listening (ETag + X-Poll-Interval)
gitrecon events repo:owner/name
gitrecon gists                      # newest public gists
gitrecon gists --user octocat
gitrecon archive 2026-10-01-0 2026-10-01-23   # GH Archive hours (UTC), streamed to disk

# look
gitrecon status                     # what is in the raw buffer
gitrecon map                        # graph summary: nodes, relations, hubs
gitrecon map --node user:octocat    # neighbors of one entity
gitrecon label                      # labels with confidence and evidence
gitrecon label --json

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

## Development

```sh
task test
```

See [AGENTS.md](AGENTS.md) for the code layout.
