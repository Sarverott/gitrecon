"""Where things live in the map, per ``datasets/imperialmap/README.md``.

- dnstrees: ``www.example.com`` -> ``com/example/www``
- ip-address-records: ``./v4/FF/FF/FF/FF``, ``./v6/FFFF/.../FFFF`` (uppercase hex,
  no padding, like the README examples ``./v4/0/0/0/0``); a network lives at
  the path of its network address.
"""

from __future__ import annotations

import ipaddress
from pathlib import PurePosixPath

DNSTREES = "dnstrees"
IP_RECORDS = "ip-address-records"
HOST_UNIONS = "host-unions"


def domain_path(domain: str) -> PurePosixPath:
    labels = [label for label in domain.lower().strip(".").split(".") if label]
    if not labels:
        raise ValueError(f"not a domain: {domain!r}")
    return PurePosixPath(*reversed(labels))


def ip_path(address: str) -> PurePosixPath:
    """Path of an address or network (``140.82.112.0/20`` -> ``v4/8C/52/70/0``)."""
    network = ipaddress.ip_network(address, strict=False)
    base = network.network_address
    if base.version == 4:
        groups = [f"{octet:X}" for octet in base.packed]
    else:
        packed = base.packed
        groups = [f"{int.from_bytes(packed[i:i + 2], 'big'):X}" for i in range(0, 16, 2)]
    return PurePosixPath(f"v{base.version}", *groups)
