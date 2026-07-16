"""Build destination / egress CIDR list artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cidr import format_list_file, merge_cidrs, parse_cidr_lines
from .fetch import extract_openai_prefixes, fetch_json, fetch_text
from .resolve import load_domains, resolve_domains

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_source(
    src: dict[str, Any],
    *,
    root: Path,
    resolve_cfg: dict[str, Any],
    warnings: list[str],
) -> tuple[str, list[str]]:
    sid = str(src.get("id") or src.get("type") or "source")
    stype = src.get("type")
    try:
        if stype == "text_url":
            text = fetch_text(src["url"])
            return sid, parse_cidr_lines(text)
        if stype == "static_file":
            text = (root / src["path"]).read_text(encoding="utf-8")
            return sid, parse_cidr_lines(text)
        if stype == "openai_json":
            payload = fetch_json(src["url"])
            return sid, extract_openai_prefixes(payload)
        if stype == "resolve":
            domains_path = root / src["domains_file"]
            domains = load_domains(domains_path)
            timeout = float(resolve_cfg.get("timeout_sec", 5))
            cidrs, per = resolve_domains(domains, timeout_sec=timeout)
            missed = [d for d, ips in per.items() if not ips]
            if missed:
                warnings.append(f"{sid}: unresolved domains: {', '.join(missed)}")
            return sid, cidrs
        warnings.append(f"{sid}: unknown source type {stype!r}")
        return sid, []
    except Exception as e:  # noqa: BLE001 — collect and continue
        warnings.append(f"{sid}: {e}")
        return sid, []


def build_named_lists(
    section: dict[str, Any],
    *,
    root: Path,
    resolve_cfg: dict[str, Any],
    warnings: list[str],
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for name, cfg in section.items():
        source_ids: list[str] = []
        groups: list[list[str]] = []
        for src in cfg.get("sources") or []:
            sid, cidrs = collect_source(src, root=root, resolve_cfg=resolve_cfg, warnings=warnings)
            source_ids.append(sid)
            if cidrs:
                groups.append(cidrs)
        results[name] = {
            "description": cfg.get("description") or name,
            "include_in_all": bool(cfg.get("include_in_all", False)),
            "sources": source_ids,
            "cidrs": merge_cidrs(groups),
        }
    return results


def write_outputs(
    *,
    out_dir: Path,
    generated_at: str,
    dest: dict[str, dict[str, Any]],
    egress: dict[str, dict[str, Any]],
    warnings: list[str],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    egress_dir = out_dir / "egress"
    egress_dir.mkdir(parents=True, exist_ok=True)

    all_groups: list[list[str]] = []
    meta_lists: dict[str, Any] = {}

    for name, item in dest.items():
        path = out_dir / f"{name}.txt"
        path.write_text(
            format_list_file(
                name=name,
                description=item["description"],
                generated_at=generated_at,
                sources=item["sources"],
                cidrs=item["cidrs"],
            ),
            encoding="utf-8",
        )
        meta_lists[name] = {
            "path": f"lists/{name}.txt",
            "count": len(item["cidrs"]),
            "sources": item["sources"],
            "include_in_all": item["include_in_all"],
            "kind": "destination",
        }
        if item["include_in_all"]:
            all_groups.append(item["cidrs"])

    all_cidrs = merge_cidrs(all_groups)
    (out_dir / "all.txt").write_text(
        format_list_file(
            name="all",
            description="Merged destination lists (include_in_all=true)",
            generated_at=generated_at,
            sources=sorted(dest.keys()),
            cidrs=all_cidrs,
        ),
        encoding="utf-8",
    )
    meta_lists["all"] = {
        "path": "lists/all.txt",
        "count": len(all_cidrs),
        "sources": sorted(dest.keys()),
        "include_in_all": False,
        "kind": "destination",
    }

    for name, item in egress.items():
        path = egress_dir / f"{name}.txt"
        path.write_text(
            format_list_file(
                name=name,
                description=item["description"],
                generated_at=generated_at,
                sources=item["sources"],
                cidrs=item["cidrs"],
            ),
            encoding="utf-8",
        )
        meta_lists[f"egress/{name}"] = {
            "path": f"lists/egress/{name}.txt",
            "count": len(item["cidrs"]),
            "sources": item["sources"],
            "include_in_all": False,
            "kind": "egress",
        }

    meta = {
        "generated_at": generated_at,
        "lists": meta_lists,
        "warnings": warnings,
        "qosnat2": {
            "alias_url_example": "https://raw.githubusercontent.com/hk59775634/ai-cidr-lists/main/lists/all.txt",
            "notes": [
                "Destination lists are for LAN client → AI service steering.",
                "lists/egress/* are vendor outbound ranges (bots/connectors calling you); do not mix into WAN egress dst_alias.",
                "Google list is intentionally broad.",
            ],
        },
    }
    meta_path = root_meta_path(out_dir)
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def root_meta_path(out_dir: Path) -> Path:
    # lists/../meta/build.json
    return out_dir.parent / "meta" / "build.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build AI service CIDR list artifacts")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--skip-egress", action="store_true")
    args = parser.parse_args(argv)

    root: Path = args.root.resolve()
    config_path = (args.config or root / "config" / "sources.json").resolve()
    out_dir = (args.out or root / "lists").resolve()

    cfg = load_config(config_path)
    resolve_cfg = cfg.get("resolve") or {}
    warnings: list[str] = []
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    dest = build_named_lists(cfg.get("lists") or {}, root=root, resolve_cfg=resolve_cfg, warnings=warnings)
    egress: dict[str, dict[str, Any]] = {}
    if not args.skip_egress:
        egress = build_named_lists(
            cfg.get("egress_lists") or {},
            root=root,
            resolve_cfg=resolve_cfg,
            warnings=warnings,
        )
        # egress section should not use include_in_all into destination all.txt
        for item in egress.values():
            item["include_in_all"] = False

    (root / "meta").mkdir(parents=True, exist_ok=True)
    write_outputs(
        out_dir=out_dir,
        generated_at=generated_at,
        dest=dest,
        egress=egress,
        warnings=warnings,
    )

    print(f"generated {generated_at}")
    for name, item in dest.items():
        print(f"  lists/{name}.txt  {len(item['cidrs'])} prefixes")
    print(f"  lists/all.txt  {sum(1 for _ in (out_dir / 'all.txt').read_text().splitlines() if _.strip() and not _.startswith('#'))} prefixes")
    for name, item in egress.items():
        print(f"  lists/egress/{name}.txt  {len(item['cidrs'])} prefixes")
    if warnings:
        print("warnings:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())