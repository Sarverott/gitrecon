# Installation

## Needs

- [uv](https://docs.astral.sh/uv/) - Python ≥ 3.12 and all dependencies
- [Task](https://taskfile.dev) - every routine is a task (`task help`)
- Node.js + npm - only for the git hooks (husky)
- optional: [GitHub CLI](https://cli.github.com) (its login is used as a token),
  [Ollama](https://ollama.com) for [[digest]]s, a Hugging Face account with write access
  to the [[atlas]]

## Setup

```sh
git clone https://github.com/Sarverott/gitrecon.git
cd gitrecon
task install        # uv sync + npm install (hooks)
task test
uv run gitrecon --help
```

## Credentials

| Variable | For | Without it |
| --- | --- | --- |
| `GITHUB_TOKEN` / `GH_TOKEN` | GitHub API | `gh auth token`, else 60 requests/hour |
| `HF_TOKEN` | pushing the map | read-only, slower downloads |
| `OLLAMA_HOST`, `OLLAMA_MODEL` | `digest` | `localhost:11434`, `llama3` |
| `XAI_API_KEY`, `XAI_MODEL` | `posts` | `posts` refuses to run |

Variables can also come from dotenv files, read in this order without overriding what
is already set: `GITRECON_ENV_FILE`, the project's `.env`, then `__WORKSHOP/forge/.env`
(a temporary home for workshop secrets).

## Where things go

| Path | What | Override |
| --- | --- | --- |
| `data/` | [[raw-buffer]], feed state, catalogs, digests, post drafts | `GITRECON_DATA` |
| `datasets/imperialmap/` | local copy of the [[atlas]] | `GITRECON_DATASETS` |

Both are git-ignored.
