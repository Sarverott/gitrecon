# internals

The workshop's own infrastructure: code hosting, local models, images, search, a
disposable browser and a wiki. Databases are shared, in `../databases`.

| Service | Image | Local address | Needs |
| --- | --- | --- | --- |
| gitea | `gitea/gitea` | `127.0.0.1:3000` (web), `:2222` (ssh) | postgres |
| ollama | `ollama/ollama` | `127.0.0.1:11435` | - |
| registry | `registry:2` | `127.0.0.1:5000` | - |
| searxng | `searxng/searxng` | `127.0.0.1:8888` | - |
| firefox | `jlesage/firefox` | `127.0.0.1:5800` (browser in the browser) | - |
| wikijs | `ghcr.io/requarks/wiki:2` | `127.0.0.1:3001` | postgres |

- **gitea** is the self-hosted remote for private scope repositories (BOS remotes policy);
  Actions are enabled for `gitea-runner` (`../runners`).
- **ollama** is published on 11435 so an ollama on the host (11434) keeps working; inside
  the network it is `http://ollama:11434`. GPU: uncomment `deploy` in `ollama.compose.yaml`
  (needs the NVIDIA container toolkit).
- **firefox** is for opening what recon finds without touching the host browser.

Start: `task services:up -- internals`, or one: `task services:up -- gitea`.
