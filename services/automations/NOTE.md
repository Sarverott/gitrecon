# automations

Things that run on their own: workflows, a search index, downloads, billing,
notifications, home automation and AI agent gateways. Databases are shared, in `../databases`.

| Service | Image | Address | Needs |
| --- | --- | --- | --- |
| n8n | `docker.n8n.io/n8nio/n8n` | `n8n.gr.rs-tech.online` | postgres |
| typesense | `typesense/typesense:29.0` | `typesense.gr.rs-tech.online` (VPN/host only) | - |
| transmission | `lscr.io/linuxserver/transmission` | `torrent.gr.rs-tech.online` (VPN/host only), peers `51413` | - |
| paymenter | `ghcr.io/paymenter/paymenter` | `shop.gr.rs-tech.online` | mariadb, redis |
| ntfy | `binwiederhier/ntfy` | `ntfy.gr.rs-tech.online` | - |
| home-assistant | `ghcr.io/home-assistant/home-assistant:stable` | `home.gr.rs-tech.online` | - |
| metamcp | `ghcr.io/metatool-ai/metamcp` ([repo](https://github.com/metatool-ai/metamcp)) | `mcp.gr.rs-tech.online` | postgres |
| openclaw | `coollabsio/openclaw` + `openclaw-browser` ([repo](https://github.com/coollabsio/openclaw)) | `claw.gr.rs-tech.online` | openclaw-browser; ollama optional |

- **typesense** publishes no `latest` tag; the version is pinned and has to be raised by hand.
- **transmission** peers on 51413 on all interfaces (torrents need to be reachable); the
  web UI is behind the gateway, VPN/host only.
- **paymenter** and **metamcp** follow their projects' example compose files, moved onto
  the shared databases.
- **openclaw** reaches models through `http://ollama:11434` (start `ollama` from internals)
  or API keys (`XAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`); set
  `OPENCLAW_PASSWORD` before using it.
- **home-assistant** behind a proxy needs `http: use_x_forwarded_for: true` and
  `trusted_proxies: [172.30.0.0/24]` in its `configuration.yaml`; device discovery would need
  `network_mode: host`.

Start: `task services:up -- automations`, or one: `task services:up -- n8n`.
