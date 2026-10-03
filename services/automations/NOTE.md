# automations

Things that run on their own: workflows, a search index, downloads, billing,
notifications, home automation and AI agent gateways. Databases are shared, in `../databases`.

| Service | Image | Local address | Needs |
| --- | --- | --- | --- |
| n8n | `docker.n8n.io/n8nio/n8n` | `127.0.0.1:5678` | postgres |
| typesense | `typesense/typesense:29.0` | `127.0.0.1:8108` | - |
| transmission | `lscr.io/linuxserver/transmission` | `127.0.0.1:9091` (web), `51413` (peers) | - |
| paymenter | `ghcr.io/paymenter/paymenter` | `127.0.0.1:8085` | mariadb, redis |
| ntfy | `binwiederhier/ntfy` | `127.0.0.1:8090` | - |
| home-assistant | `ghcr.io/home-assistant/home-assistant:stable` | `127.0.0.1:8123` | - |
| metamcp | `ghcr.io/metatool-ai/metamcp` ([repo](https://github.com/metatool-ai/metamcp)) | `127.0.0.1:12008` | postgres |
| openclaw | `coollabsio/openclaw` + `openclaw-browser` ([repo](https://github.com/coollabsio/openclaw)) | `127.0.0.1:18080` | openclaw-browser; ollama optional |

- **typesense** publishes no `latest` tag; the version is pinned and has to be raised by hand.
- **transmission** peers on 51413 on all interfaces (torrents need to be reachable); the
  web UI stays on localhost.
- **paymenter** and **metamcp** follow their projects' example compose files, moved onto
  the shared databases.
- **openclaw** reaches models through `http://ollama:11434` (start `ollama` from internals)
  or API keys (`XAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`); set
  `OPENCLAW_PASSWORD` before using it.
- **home-assistant** needs `network_mode: host` instead of the port for device discovery.

Start: `task services:up -- automations`, or one: `task services:up -- n8n`.
