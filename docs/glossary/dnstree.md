# DNS tree

> Domains as a reversed directory tree: `www.example.com` -> `dnstrees/com/example/www`.

## What it is

Each domain node holds `.holders.yml`: the links seen on that domain and the [[host-union]]s that point at them.

## Where

`gitrecon.atlas.paths.domain_path()`, `AtlasUpdate.add_links()`.

## Relations

Filled from the [[link-catalog]]; an [[area]] of the [[atlas]].
