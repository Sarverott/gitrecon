# networking

How the workshop meets the outside: the edge proxy, the VPN, abuse protection and one
directory of users.

| Service | Image | Address | Notes |
| --- | --- | --- | --- |
| traefik | `traefik:v3` | `127.0.0.1:80/443`, dashboard `127.0.0.1:8081` | services opt in with `traefik.enable=true` labels |
| wireguard | `lscr.io/linuxserver/wireguard` | `0.0.0.0:51820/udp` | peers' configs in its `/config` volume |
| crowdsec | `crowdsecurity/crowdsec` | - | reads traefik's access log |
| openldap | `osixia/openldap` | `127.0.0.1:389`, `:636` | users for gitea, wikijs and others |

- Everything listens on localhost until `BIND` (or `TRAEFIK_BIND`) is set; **wireguard**
  is the exception, because a VPN must be reachable.
- No service carries traefik labels yet: routes get added once domains are decided.
- crowdsec only detects for now; blocking needs a bouncer (e.g. the traefik plugin).

Start: `task services:up -- networking`, or one: `task services:up -- traefik`.

## Worth a look later

- [containernetworking/cni](https://github.com/containernetworking/cni) - container network plugins
- [pikpikcu/airecon](https://github.com/pikpikcu/airecon) - AI-assisted recon
- [polonskiy/crowdr](https://github.com/polonskiy/crowdr) - docker container orchestration in bash
