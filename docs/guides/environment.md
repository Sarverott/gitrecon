# The services environment

Around gitrecon runs an environment of [[services]]: databases, a git server, local
models, search, automations, the network edge and runners. All of it is docker compose,
one file per service:

```
compose.yaml                        gitrecon itself + include: services/compose.yaml
services/
├── compose.yaml                    includes the groups
├── control.py                      starts targets with their dependencies
├── .env.example                    every setting, with its default
├── databases/   NOTE.md compose.yaml postgres mariadb redis chromadb
├── internals/   NOTE.md compose.yaml gitea ollama registry searxng firefox wikijs
├── automations/ NOTE.md compose.yaml n8n typesense transmission paymenter ntfy
│                                     home-assistant metamcp openclaw
├── networking/  NOTE.md compose.yaml traefik wireguard crowdsec openldap
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
```

Nothing starts by accident: every service sits behind two profiles, its group and its own
name. Compose leaves out services of disabled profiles entirely, so `services/control.py`
reads the resolved model, follows `depends_on` across groups and enables exactly what the
targets need.

## Settings and safety

- Every published port is bound to `127.0.0.1` until `BIND` says otherwise (wireguard and
  transmission's peer port are the exceptions - they must be reachable).
- Defaults are development passwords. Copy what you change from `services/.env.example`
  into `.env`; the tasks also read the forge `.env`.
- `postgres` creates one database and owner per app on its first start
  (`POSTGRES_MULTIPLE_DATABASES`); apps log in with `POSTGRES_PASSWORD`.
- The GitHub runner is ephemeral (one job per container) and takes its token from
  `GITHUB_RUNNER_TOKEN` or `gh auth token`; never route fork pull requests to it.

The web interface (`app/`) is not here yet on purpose: first the environment, the command
line and the terminal interface.
