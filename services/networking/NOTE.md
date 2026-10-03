# networking

How the workshop meets the outside. Main domain: **gr.rs-tech.online** (routing rules, the
wildcard certificate, the LDAP base `dc=gr,dc=rs-tech,dc=online`).

| Service | Image | Address | Role |
| --- | --- | --- | --- |
| traefik | `traefik:v3` | `172.30.0.10`; host `127.0.0.1:8880` (http), `:8843` (https), `:2222` (gitea ssh) | the gateway: every web service as `<name>.gr.rs-tech.online` |
| dnsmasq | `dockurr/dnsmasq` | `172.30.0.53` | DNS of the bubble |
| wireguard | `lscr.io/linuxserver/wireguard` | `172.30.0.2`; host `0.0.0.0:51820/udp` | the bubble: VPN into the project network |
| cloudflared | `cloudflare/cloudflared` | - | public access through a Cloudflare Tunnel |
| ngrok | `ngrok/ngrok` | inspector `ngrok.gr.rs-tech.online` | public access through ngrok |
| crowdsec | `crowdsecurity/crowdsec` | - | reads traefik's access log, detects abuse |
| openldap | `osixia/openldap` | `openldap:389` (inside) | one directory of users |

Setup files live in `config/`: `traefik.yml` (static: entrypoints, providers, certificates),
`traefik/dynamic.yml` (middlewares, the dashboard - watched, changes apply live),
`dnsmasq/gitrecon.conf`, `ngrok.yml`.

## Closed by default

No service publishes a port except traefik (the gateway), wireguard (a VPN must be
reachable) and transmission's peer port. Everything else is reached one of three ways:

1. **On this host:** `http://<name>.localhost:8880` - browsers resolve `*.localhost` to the
   host by themselves; `https://…:8843` too (default certificate until the wildcard one exists).
2. **Through the bubble (WireGuard):** peers get `10.13.13.0/24`, a route to the project
   network `172.30.0.0/24` only (split tunnel) and dnsmasq as DNS, which answers
   `*.gr.rs-tech.online` with traefik and container names (`postgres`, `openldap`, `nats`)
   with their addresses. So `https://git.gr.rs-tech.online` and `psql -h postgres` both work
   on a peer, with nothing published. Peer configs and QR codes: the `wireguard-config` drive
   (`peer1/peer1.conf`, `PEERS=n` for more).
3. **Publicly, only when chosen:** cloudflared and ngrok forward to traefik's `public`
   entrypoint (`:8000`, never published), where only routers that name it answer - today
   just `PathPrefix(/hooks)` of the webhook receiver. Add a public route with labels:
   `traefik.http.routers.<name>-public.entrypoints: public` and a rule.

`vpn-only` (`config/traefik/dynamic.yml`) guards admin tools - traefik's dashboard, ollama,
registry, chromadb, typesense, transmission, firefox, nats: host, project network and VPN only.

## What the outside needs

- **Wildcard certificate:** `CF_DNS_API_TOKEN` (Cloudflare API token with *Zone DNS edit* on
  rs-tech.online); traefik then gets `gr.rs-tech.online` + `*.gr.rs-tech.online` from
  Let's Encrypt by DNS challenge - works without any open port. ACME email:
  `hostmaster@gr.rs-tech.online` in `config/traefik.yml`.
- **VPN endpoint:** a DNS-only (not proxied) record such as `vpn.gr.rs-tech.online` → this
  host's public address, then `WIREGUARD_SERVER_URL=vpn.gr.rs-tech.online`; UDP 51820 open
  on the router/firewall.
- **Cloudflare Tunnel:** create it in Zero Trust → Networks → Tunnels, copy its token to
  `CLOUDFLARE_TUNNEL_TOKEN`, and point public hostnames at `http://traefik:8000`.
- **ngrok:** `NGROK_AUTHTOKEN`; a fixed free domain goes into `config/ngrok.yml`.

## On a host with Coolify

Coolify's proxy holds 80/443 here, so traefik defaults to 8880/8843. To serve
`*.gr.rs-tech.online` on 443 anyway, route that domain in Coolify's proxy to
`http://<host>:8880` (or give traefik 80/443 on a host without another proxy:
`TRAEFIK_HTTP_PORT=80 TRAEFIK_HTTPS_PORT=443`).

Start: `task services:up -- networking`, or the bubble alone: `task services:up -- wireguard`
(dnsmasq comes along), the gateway: `task services:up -- traefik`.

## Worth a look later

- [containernetworking/cni](https://github.com/containernetworking/cni) - container network plugins
- [pikpikcu/airecon](https://github.com/pikpikcu/airecon) - AI-assisted recon
- [polonskiy/crowdr](https://github.com/polonskiy/crowdr) - docker container orchestration in bash
