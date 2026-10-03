# databases

Shared databases: **one instance of each**, used by the services of every other group.
Each service has its own `<name>.compose.yaml`, listed in this folder's `compose.yaml`.

| Service | Image | Address | Used by |
| --- | --- | --- | --- |
| postgres | `postgres:17-alpine` | `postgres:5432` (inside) | gitea, wikijs, n8n, metamcp |
| mariadb | `mariadb:11` | `mariadb:3306` (inside) | paymenter |
| redis | `redis:7-alpine` | `redis:6379` (inside) | paymenter (cache and queue) |
| chromadb | `chromadb/chroma` | `chroma.gr.rs-tech.online` (VPN/host only) | embeddings of collected data |

- **postgres** creates one database and owner per name in `POSTGRES_MULTIPLE_DATABASES`
  (default `gitea,wikijs,n8n,metamcp`) on its first start (`postgres/init-databases.sh`);
  every owner's password is `POSTGRES_PASSWORD`. A database added later needs
  `CREATE USER` / `CREATE DATABASE` by hand, or a fresh volume.
- **mariadb vs mysql:** MariaDB - Paymenter's own example uses it, and it is the default
  MySQL-compatible server in most distributions.
- **redis** was not on the first list; Paymenter needs it.
- Defaults are development passwords (`gitrecon`); databases publish no port - reach them
  by name from the project network or the WireGuard bubble. Set real ones in `.env` before exposing anything (`services/.env.example`).

Start: `task services:up -- databases` (or just the services that need them - they come along).
