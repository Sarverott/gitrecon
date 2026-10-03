# Link catalog

> Every URL found in cloned gists, classified by what it can feed.

## What it is

Kinds: `feed`, `github-api`, `github-user`, `github-repo`, `gist`, `github-pages`, `pattern` (URLs with placeholders such as `https://gist.github.com/{USER}.atom`), `package-registry`, `dataset-hub`, `wiki`, `search`, `site`. Each link keeps every place it was found (`file:line`). Only directories whose git remote is gist.github.com are read (`--all` reads every note).

## Where

`gitrecon.sources.links`; saved to `data/catalog/links.jsonl`. CLI: `gitrecon links .. --save`.

## Relations

Feeds go to [[news-feed]] reading; domains to [[dnstree]]s and a [[host-union]]; GitHub accounts to the [[user-namespace]].
