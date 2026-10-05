# Documentation

These pages are plain markdown in `docs/`:

- an **Obsidian vault** - open `docs/` in Obsidian; pages link with `[[wikilinks]]`,
- a **MkDocs** site (Material theme) - `docs/` is its own small uv project
  (`docs/pyproject.toml`), built by **Read the Docs** from `.readthedocs.yaml`,
- **terminal manuals** - `task manuals` lists the pages, `task manuals -- user-namespace`
  renders one.

| Task | Does |
| --- | --- |
| `task manuals [-- PAGE]` | read the docs in the terminal |
| `task docs:serve` | live preview at http://127.0.0.1:8000 |
| `task docs:build` | build into `site/`, failing on any warning (as Read the Docs does) |
| `task docs:lock` | after editing `docs/pyproject.toml`: refresh the lock and `requirements.txt` |

Layout:

| Folder | Holds |
| --- | --- |
| `glossary/` | one page per element - what it is, where it lives, relations |
| `guides/` | how to do things |
| `_mkdocs/` | the wikilinks hook |

A new glossary page also goes into the glossary index (`glossary/README.md`) and the
`nav` of `mkdocs.yml`.

## Scrapnotes

`task scrapnote` (or `task scrapnote -- "a title"`) starts `docs/devlog/scrapnote-<UNIXUSAT>.md`,
named by the current moment in milliseconds, and prints its path:
`$EDITOR "$(task scrapnote)"`.
