"""CIDR helpers for ai-cidr-lists."""

from __future__ import annotations

import ipaddress
from typing import Iterable


def normalize_cidr(token: str) -> str:
    token = token.strip()
    if not token:
        raise ValueError("empty")
    if "/" not in token:
        ip = ipaddress.ip_address(token)
        if ip.version != 4:
            raise ValueError(f"IPv6 not supported yet: {token}")
        return str(ipaddress.ip_network(f"{token}/32", strict=False))
    net = ipaddress.ip_network(token, strict=False)
    if net.version != 4:
        raise ValueError(f"IPv6 not supported yet: {token}")
    return str(net)


def parse_cidr_lines(text: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        if not line:
            continue
        cidr = normalize_cidr(line)
        if cidr in seen:
            continue
        seen.add(cidr)
        out.append(cidr)
    return out


def merge_cidrs(groups: Iterable[Iterable[str]]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        for item in group:
            cidr = normalize_cidr(item)
            if cidr in seen:
                continue
            seen.add(cidr)
            out.append(cidr)
    # Sort by network address then prefix length for stable diffs.
    return sorted(out, key=lambda c: (ipaddress.ip_network(c).network_address, ipaddress.ip_network(c).prefixlen))


def format_list_file(
    *,
    name: str,
    description: str,
    generated_at: str,
    sources: list[str],
    cidrs: list[str],
) -> str:
    lines = [
        f"# {name}",
        f"# {description}",
        f"# generated: {generated_at}",
        f"# count: {len(cidrs)}",
        f"# sources: {', '.join(sources) if sources else '(none)'}",
        "# format: one IPv4 CIDR per line — compatible with qosnat2 Alias.url",
        "",
    ]
    lines.extend(cidrs)
    lines.append("")
    return "\n".join(lines)