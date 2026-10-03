# Gist

> A GitHub gist: files, owner, description - and, for gitrecon, a notebook full of links.

## What it is

Public gists are discovered through `/gists/public` and a user's gists through `/users/{u}/gists`. Gists cloned next to the project are read for links into the [[link-catalog]].

A user's gists can be described as a catalog - `gist_catalog(username)` gives
`{gistID, filelist, description, stars, comments, forks, commits, size, public, created_at, url}`
per gist (GraphQL, 100 per request; secret gists only with the owner's token) - and cloned
as they are with `clone_gists(catalog, path)` into `path/<gistID>`.

## Where

`gitrecon.models.Gist`, `gitrecon.sources.gists`. CLI: `gitrecon gists [--user NAME]`,
`gitrecon gist-catalog USER`, `gitrecon gist-clone USER PATH`; example `examples/data-sources/05-my-gists.ipynb`.

## Relations

Mapped in the [[activity-graph]] (`created_gist`); `mass-gist-drop` is a [[label]] about them.
