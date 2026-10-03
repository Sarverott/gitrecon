# Gateway

> Traefik as the only way in: every web service is `<name>.gr.rs-tech.online`, nothing else publishes a port.

## What it is

Services carry traefik labels (`Host(<name>.gr.rs-tech.online) || Host(<name>.localhost)`);
traefik is reached on the host (`127.0.0.1:8880`/`8843`), from the WireGuard **bubble**
(peers routed into the project network `172.30.0.0/24`, with dnsmasq answering the domain
with traefik's `172.30.0.10` and container names with their addresses), or - only for
routers marked so - from tunnels (cloudflared, ngrok) on the `public` entrypoint.
`vpn-only` guards admin tools. A wildcard certificate comes from Let's Encrypt by
Cloudflare DNS challenge.

## Where

`services/networking/`: `config/traefik.yml` (static), `config/traefik/dynamic.yml`,
`config/dnsmasq/gitrecon.conf`, `config/ngrok.yml`, the compose files of traefik, dnsmasq,
wireguard, cloudflared, ngrok; the project network in the root `compose.yaml`;
`task services:list` shows every address. Guide: the services environment.

## Relations

Part of the [[services]]; LDAP's base comes from the same domain.
