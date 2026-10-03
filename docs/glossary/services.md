# Services

> The environment around gitrecon: docker compose services in five groups, started with their dependencies.

## What it is

`databases` (postgres, mariadb, redis, chromadb), `internals` (gitea, ollama, registry,
searxng, firefox, wikijs), `automations` (n8n, typesense, transmission, paymenter, ntfy,
home-assistant, metamcp, openclaw), `networking` (traefik, wireguard, crowdsec, openldap)
and `runners` (github-runner, gitea-runner, scheduler, webhook, nats). Each service has
profiles `[group, name]`; databases are shared; every volume is a folder in
`datasets/_dockdrives/` (declared in `services/volumes.compose.yaml`).

## Where

`services/<group>/<service>.compose.yaml`, the group's `compose.yaml` and `NOTE.md`;
`services/control.py`; `task services:list|up|down|ps|logs|pull|drives|backup`. Guide: the services
environment (`guides/environment.md`).

## Relations

The [[menu]] lists the `services:*` tasks; the GitHub runner can run the jobs of the
[[craft-loop]]; ollama serves [[digest]]s.
