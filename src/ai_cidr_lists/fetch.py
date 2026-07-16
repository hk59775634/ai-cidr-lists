"""HTTP fetch helpers (stdlib only)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

USER_AGENT = "ai-cidr-lists/0.1 (+https://github.com/hk59775634/ai-cidr-lists)"
DEFAULT_TIMEOUT = 60


def fetch_bytes(url: str, *, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} for {url}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"fetch failed for {url}: {e}") from e


def fetch_text(url: str, *, timeout: int = DEFAULT_TIMEOUT) -> str:
    return fetch_bytes(url, timeout=timeout).decode("utf-8", errors="replace")


def fetch_json(url: str, *, timeout: int = DEFAULT_TIMEOUT) -> Any:
    return json.loads(fetch_text(url, timeout=timeout))


def extract_openai_prefixes(payload: Any) -> list[str]:
    """OpenAI JSON uses {creationTime, prefixes:[{ipv4Prefix|ipv6Prefix}, ...]}."""
    out: list[str] = []
    prefixes = payload.get("prefixes") if isinstance(payload, dict) else None
    if not isinstance(prefixes, list):
        return out
    for item in prefixes:
        if not isinstance(item, dict):
            continue
        v4 = item.get("ipv4Prefix") or item.get("ipv4_prefix")
        if isinstance(v4, str) and v4.strip():
            out.append(v4.strip())
    return out