"""DNS resolve domains to IPv4 /32 via multiple resolvers (stdlib)."""

from __future__ import annotations

import concurrent.futures
import socket
from pathlib import Path


def load_domains(path: Path) -> list[str]:
    domains: list[str] = []
    seen: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        host = line.lower().rstrip(".")
        if not host or host in seen:
            continue
        seen.add(host)
        domains.append(host)
    return domains


def _resolve_one(domain: str, timeout: float) -> list[str]:
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        infos = socket.getaddrinfo(domain, None, socket.AF_INET, socket.SOCK_STREAM)
    except (socket.gaierror, socket.timeout, OSError):
        return []
    finally:
        socket.setdefaulttimeout(old)

    addrs: list[str] = []
    seen: set[str] = set()
    for info in infos:
        ip = info[4][0]
        if ip in seen:
            continue
        seen.add(ip)
        addrs.append(f"{ip}/32")
    return addrs


def resolve_domains(
    domains: list[str],
    *,
    timeout_sec: float = 5.0,
    workers: int = 16,
) -> tuple[list[str], dict[str, list[str]]]:
    """Return (merged /32 list, per-domain map). Uses system resolver."""
    per_domain: dict[str, list[str]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_resolve_one, d, timeout_sec): d for d in domains}
        for fut in concurrent.futures.as_completed(futs):
            domain = futs[fut]
            try:
                per_domain[domain] = fut.result()
            except Exception:
                per_domain[domain] = []

    merged: list[str] = []
    seen: set[str] = set()
    for domain in domains:
        for cidr in per_domain.get(domain, []):
            if cidr in seen:
                continue
            seen.add(cidr)
            merged.append(cidr)
    return merged, per_domain