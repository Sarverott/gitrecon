# internals

The workshop's own infrastructure: code hosting, local models, images, search, a
disposable browser and a wiki. Databases are shared, in `../databases`.

| Service | Image | Address | Needs |
| --- | --- | --- | --- |
| gitea | `gitea/gitea` | `git.gr.rs-tech.online`, ssh `:2222` via traefik | postgres |
| ollama | `ollama/ollama` | `ollama.gr.rs-tech.online` (VPN/host only) | - |
| registry | `registry:2` | `registry.gr.rs-tech.online` (VPN/host only) | - |
| searxng | `searxng/searxng` | `search.gr.rs-tech.online` | - |
| firefox | `jlesage/firefox` | `firefox.gr.rs-tech.online` (VPN/host only) | - |
| wikijs | `ghcr.io/requarks/wiki:2` | `wiki.gr.rs-tech.online` | postgres |

- **gitea** (`git.gr.rs-tech.online`, ssh on 2222 through traefik) is the self-hosted remote for private scope repositories (BOS remotes policy);
  Actions are enabled for `gitea-runner` (`../runners`).
- **ollama** is `http://ollama:11434` inside the network and `ollama.gr.rs-tech.online` through
  the gateway; an ollama on the host keeps its own 11434. GPU: uncomment `deploy` in `ollama.compose.yaml`
  (needs the NVIDIA container toolkit).
- **firefox** is for opening what recon finds without touching the host browser.

Start: `task services:up -- internals`, or one: `task services:up -- gitea`.
