# Examples

Runnable notebooks live in `examples/<title>/`, one folder per example:

```
examples/<example-title>/
├── README.md          what it shows
├── Taskfile.yml       includes ../Taskfile.notebooks.yml
├── notebook.ipynb     one notebook...
└── 01-<chapter>.ipynb ...or numbered chapters
```

| Task | Does |
| --- | --- |
| `task examples:list` | examples and their notebooks |
| `task examples:launch` | Jupyter on all examples |
| `task examples:run [-- TITLE...]` | execute headless; copies in `<title>/.out/` |
| `task examples:marimo` | convert every notebook to a marimo app (`<title>/marimo/`) |
| `task examples:clean` | clear outputs before committing |

Inside one folder: `task launch | run | marimo | marimo:edit | clean`.

Notebooks are committed without outputs; `.out/` and `marimo/` are generated and
git-ignored. A notebook that writes somewhere public (like `map-dataset/03-push`) only does
so behind an explicit flag.
