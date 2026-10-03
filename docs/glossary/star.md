# Star

> One user starring one repository, at a known time.

## What it is

Fetched with the `application/vnd.github.star+json` media type, so each repository comes with `starred_at`. A full listing of an active account can be thousands of repositories (30+ pages).

## Where

`gitrecon.models.Star`, `gitrecon.sources.stars`. CLI: `gitrecon stars sarverott [--json] [--save]`.

## Relations

Owners of starred repositories become [[identity|identities]] in the [[user-namespace]]; stars can be summarized into a [[digest]].
