# Host union

> Relations between URLs, domains, IPs and services, grouped by where they came from.

## What it is

`host-unions/<union>/.index.json`. `gist-harvest`: every harvested URL with its domain, kind and where it was found. `github-meta`: GitHub's domains per service and how many networks each has.

## Where

`AtlasUpdate.add_links(..., union=...)`, `add_github_meta()`.

## Relations

Pointed at by [[dnstree]] holders and [[ip-address-record]]s; an [[area]] of the [[atlas]].
