# The services environment

Around gitrecon runs an environment of [[services]]: databases, a git server, local
models, search, automations, the network edge and runners. All of it is docker compose,
one file per service:

```
compose.yaml                        gitrecon itself + include: services/compose.yaml
services/
├── compose.yaml                    includes the groups
├── control.py                      starts targets with their dependencies; drives, backup
├── volumes.compose.yaml            every volume, as a folder in datasets/_dockdrives/
├── .env.example                    every setting, with its default
├── databases/   NOTE.md compose.yaml postgres mariadb redis chromadb
├── internals/   NOTE.md compose.yaml gitea ollama registry searxng firefox wikijs
├── automations/ NOTE.md compose.yaml n8n typesense transmission paymenter ntfy
│                                     home-assistant metamcp openclaw
├── networking/  NOTE.md compose.yaml traefik dnsmasq wireguard cloudflared ngrok
│                config/ (traefik.yml, traefik/dynamic.yml, dnsmasq/, ngrok.yml) crowdsec openldap
└── runners/     NOTE.md compose.yaml github-runner gitea-runner scheduler webhook nats
```

Each group's `NOTE.md` has the table of its services: image, local address, what it needs.

## Using it

```sh
task services:list                       # every service: group, image, ports, dependencies
task services:up -- databases            # a whole group
task services:up -- gitea n8n            # services - postgres comes along by itself
task services:ps
task services:logs -- gitea
task services:down                       # stops everything; volumes (the data) stay
task services:drives                     # every volume's folder: exists, size, users, engine
task services:backup                     # archive them into datasets/_backups/ (or name volumes)
```

## The gateway and the bubble

Only traefik publishes ports (plus wireguard's UDP and transmission's peers): every web
service is `<name>.gr.rs-tech.online` - see [[gateway]] and `services/networking/NOTE.md`.

| From | How | Example |
| --- | --- | --- |
| this host | `*.localhost` resolves to the host by itself | `http://git.localhost:8880` |
| the WireGuard bubble | peers route into `172.30.0.0/24`, dnsmasq is their DNS | `https://git.gr.rs-tech.online`, `psql -h postgres` |
| the internet | cloudflared / ngrok → traefik's `public` entrypoint, only routers marked public | `https://<tunnel>/hooks/...` |

Traefik's host ports default to 8880/8843 because a Coolify proxy holds 80/443 on this
host; set `TRAEFIK_HTTP_PORT`/`TRAEFIK_HTTPS_PORT` where nothing does. The wildcard
certificate needs `CF_DNS_API_TOKEN`; the VPN endpoint a DNS-only record such as
`vpn.gr.rs-tech.online` and `WIREGUARD_SERVER_URL`.

## Where the data lives

Every volume is declared once, in `services/volumes.compose.yaml`, as a bind mount of
`${REPO_DIR}/datasets/_dockdrives/<volume>`. All service data is therefore one folder:
easy to check, to back up, or to move to another disk. `REPO_DIR` is the repository root;
the tasks and `control.py` set it, plain `docker compose` falls back to the current
directory (run it from the root).

- `task services:up` creates the folders its services need (a bind mount fails on a
  missing folder).
- Services write their folders as their own users (postgres: uid 70, mode 700), so you
  may not read them directly. `task services:drives` says `no access` for those;
  `task services:backup` archives from inside a short-lived container and hands you the
  archive. It refuses while a service using those volumes runs (`--live` to insist).
- A volume created by the engine with another path shows as `other path` in `drives`:
  `docker volume rm gitrecon_<volume>` and start again - the data stays in its folder.

Containers and volumes are read through the docker SDK (podman's when no docker socket
answers); compose itself (includes, profiles, up, down, pull, logs) runs as `docker compose`,
which neither Python package implements.

Nothing starts by accident: every service sits behind two profiles, its group and its own
name. Compose leaves out services of disabled profiles entirely, so `services/control.py`
reads the resolved model, follows `depends_on` across groups and enables exactly what the
targets need.

## Settings and safety

- Services publish no ports; traefik's are bound to `127.0.0.1` until `BIND` says otherwise.
- Defaults are development passwords. Copy what you change from `services/.env.example`
  into `.env`; the tasks also read the forge `.env`.
- `postgres` creates one database and owner per app on its first start
  (`POSTGRES_MULTIPLE_DATABASES`); apps log in with `POSTGRES_PASSWORD`.
- The GitHub runner is ephemeral (one job per container) and takes its token from
  `GITHUB_RUNNER_TOKEN` or `gh auth token`; never route fork pull requests to it.

The web interface (`app/`) is not here yet on purpose: first the environment, the command
line and the terminal interface.
