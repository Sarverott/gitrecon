# IP address record

> A network at the path of its address: `140.82.112.0/20` -> `ip-address-records/v4/8C/52/70/0`.

## What it is

Uppercase hex, no padding (`v4/0/0/0/0`, `v6/FFFF/.../FFFF`). The node's `.index.json` lists the CIDRs there and the services behind them (from GitHub `/meta`: `web`, `api`, `git`, `hooks`, ...). The ~7k GitHub Actions ranges are skipped unless asked for (`--heavy`).

## Where

`gitrecon.atlas.paths.ip_path()`, `AtlasUpdate.add_github_meta()`.

## Relations

Linked to the `github-meta` [[host-union]]; an [[area]] of the [[atlas]].
