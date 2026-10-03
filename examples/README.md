# gitrecon examples

Runnable Jupyter notebooks that show how to use gitrecon from Python: concrete
constructor calls, step by step, with the matching CLI commands.

| Example | Notebooks | Shows |
| --- | --- | --- |
| [getting-started](getting-started/) | `notebook.ipynb` | `Config`, `GitHubClient`, models, starred repositories, `RawBuffer`, `to_json()` / `html_url` for other programs |
| [activity-labels](activity-labels/) | `notebook.ipynb` | events feed, GH Archive hour, `ActivityGraph`, `Labeler` + `Thresholds` |
| [data-sources](data-sources/) | `01-gist-links` … `04-blog` | gist link harvest, RSS/Atom feeds, RFC index, blog articles |
| [map-dataset](map-dataset/) | `01-dataset` … `03-push` | the Hugging Face map: pull, write findings, user-namespace, push |
| [text-experiments](text-experiments/) | `notebook.ipynb` | markdown, word-chains, a12y numeronyms, RAT scripts, Lark JSON tree |

## Running

```sh
task examples:list                       # what is here
task examples:launch                     # Jupyter on all examples
task examples:run                        # execute all headless (copies in <title>/.out/)
task examples:run -- getting-started     # just one
task examples:marimo                     # convert all notebooks to marimo apps
```

Inside one example folder: `task launch | run | marimo | marimo:edit | clean`.

Notebooks reach the network (GitHub API, feeds, Hugging Face). Credentials come from
the environment or dotenv files (`gitrecon.config.load_env`). `map-dataset/03-push`
only pushes when you set `PUSH = True`.

## Adding an example

```
examples/<example-title>/
├── README.md          what it shows, how to run it
├── Taskfile.yml       includes ../Taskfile.notebooks.yml (copy it from another example)
├── notebook.ipynb     one notebook...
└── 01-<chapter>.ipynb ...or numbered chapters
```

Commit notebooks without outputs (`task clean`); executed copies (`.out/`) and marimo
conversions (`marimo/`) are generated and git-ignored.
