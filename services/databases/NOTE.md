# databases

Shared databases: **one instance of each**, used by the services of every other group.
Each service has its own `<name>.compose.yaml`, listed in this folder's `compose.yaml`.

| Service | Image | Local address | Used by |
| --- | --- | --- | --- |
| postgres | `postgres:17-alpine` | `127.0.0.1:5432` | gitea, wikijs, n8n, metamcp |
| mariadb | `mariadb:11` | `127.0.0.1:3306` | paymenter |
| redis | `redis:7-alpine` | `127.0.0.1:6379` | paymenter (cache and queue) |
| chromadb | `chromadb/chroma` | `127.0.0.1:8000` | embeddings of collected data |

- **postgres** creates one database and owner per name in `POSTGRES_MULTIPLE_DATABASES`
  (default `gitea,wikijs,n8n,metamcp`) on its first start (`postgres/init-databases.sh`);
  every owner's password is `POSTGRES_PASSWORD`. A database added later needs
  `CREATE USER` / `CREATE DATABASE` by hand, or a fresh volume.
- **mariadb vs mysql:** MariaDB - Paymenter's own example uses it, and it is the default
  MySQL-compatible server in most distributions.
- **redis** was not on the first list; Paymenter needs it.
- Defaults are development passwords (`gitrecon`) and every port is published to
  localhost only. Set real ones in `.env` before exposing anything (`services/.env.example`).

Start: `task services:up -- databases` (or just the services that need them - they come along).
