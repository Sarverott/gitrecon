# runners

What runs jobs: CI runners, scheduled jobs, webhook-triggered jobs, and a message bus
between them.

| Service | Image | Address | Needs |
| --- | --- | --- | --- |
| github-runner | built from `github-runner/` | - | `GITHUB_RUNNER_TOKEN` (or the gh CLI login) |
| gitea-runner | `gitea/act_runner` | - | gitea, `GITEA_RUNNER_TOKEN` |
| scheduler | `mcuadros/ofelia` | - | docker socket |
| webhook | `almir/webhook` | `hooks.gr.rs-tech.online`; public `/hooks` through the tunnels | hooks in `webhook/hooks.json` |
| nats | `nats` (JetStream) | `nats:4222` (inside), monitor `nats.gr.rs-tech.online` | - |

- **github-runner** is the ephemeral runner from shakespeare-mobile's `gh-runners`: one job
  per container, the token never reaches the jobs, the runner version pinned with its
  checksum (`task services:runner:versions` prints the newest). It serves
  `GITHUB_RUNNER_REPOSITORY` (default `Sarverott/gitrecon`) with the label `gitrecon`;
  `GITHUB_RUNNERS=n` starts more. `task services:up -- github-runner` takes the token from
  `gh auth token` - a fine-grained token with *Administration: read and write* on the
  repository is the least privilege.
- Public repositories: never send `pull_request` jobs from forks to self-hosted runners.
- **gitea-runner** registers with a token from gitea → Site Administration → Actions → Runners.
- **scheduler** runs jobs declared as labels on other services (see `scheduler.compose.yaml`).
- **webhook** starts with a `ping` hook: `curl http://hooks.localhost:8880/hooks/ping`; it is
  the one service public through the tunnels (`/hooks` on traefik's `public` entrypoint).

Start: `task services:up -- runners`, or one: `task services:up -- nats`.
