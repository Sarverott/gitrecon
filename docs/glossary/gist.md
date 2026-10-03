# Gist

> A GitHub gist: files, owner, description - and, for gitrecon, a notebook full of links.

## What it is

Public gists are discovered through `/gists/public` and a user's gists through `/users/{u}/gists`. Gists cloned next to the project are read for links into the [[link-catalog]].

## Where

`gitrecon.models.Gist`, `gitrecon.sources.gists`. CLI: `gitrecon gists [--user NAME]`.

## Relations

Mapped in the [[activity-graph]] (`created_gist`); `mass-gist-drop` is a [[label]] about them.
