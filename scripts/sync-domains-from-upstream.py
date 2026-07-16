#!/usr/bin/env python3
"""Sync domains/ from VPSDance/ai-proxy-rules (+ Cursor extras + CN AI).

Usage:
  python3 scripts/sync-domains-from-upstream.py [--repo /tmp/ai-proxy-rules]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = Path("/tmp/ai-proxy-rules")
UPSTREAM = "https://github.com/VPSDance/ai-proxy-rules.git"

SKIP_LISTS = {"all", "coding", "media", "model"}

FILE_MAP = {
    "x-ai": "xai",
    "copilot": "microsoft-ai",
}

GENERIC_SUFFIX_DENY = {
    "auth0.com", "algolia.net", "algolianet.com", "sentry.io", "segment.io",
    "intercom.io", "intercomcdn.com", "launchdarkly.com", "featuregates.org",
    "statsig.com", "statsigapi.net", "api.statsig.com", "events.statsigapi.net",
    "cloudflareinsights.com", "static.cloudflareinsights.com",
    "challenges.cloudflare.com", "identrust.com", "observeit.net",
    "datadoghq.com", "browser-intake-datadoghq.com", "browser-intake-us5-datadoghq.com",
    "growthbook.io", "cdn.growthbook.io", "usefathom.com", "cdn.usefathom.com",
    "arkoselabs.com", "client-api.arkoselabs.com",
    "microsoftapp.net", "api.microsoftapp.net",
    "livekit.cloud", "imgix.net", "ghost.io", "b-cdn.net",
    "amazonaws.com", "cloudinary.com", "azureedge.net", "azurefd.net",
    "blob.core.windows.net", "windows.net", "msecnd.net", "visualstudio.com",
    "googleapis.com", "gstatic.com", "google.com", "clients6.google.com",
    "github.com", "githubusercontent.com", "githubnext.com",
    "msn.com", "bing.com", "officeapps.live.com", "microsoft.com",
    "live.com", "office.com", "cloudflare.net",
    "stripe.com", "stripe.network",
}

# Upstream noise / overly broad / unrelated (even if listed under Core)
HARD_DENY = {
    "stripe.com", "interface.feedback", "lcicat.org", "lcicollections.org",
    "mcpservertest.online", "muthos.com", "sillylittleguy.org",
    "static.cloudflareinsights.com", "chatgpt.livekit.cloud",
}

THIRD_PARTY_ALLOW_EXACT = {
    "openai-api.arkoselabs.com",
    "openaiassets.blob.core.windows.net",
    "openaicom-api-bdcpf8c6d2e9atf6.z01.azurefd.net",
    "openaicomproductionae4b.blob.core.windows.net",
    "production-openaicom-storage.azureedge.net",
    "openaiapi-site.azureedge.net",
    "anthropic-com.ghost.io",
    "anthropic.auth0.com",
    "anthropic.com.cdn.cloudflare.net",
    "servd-anthropic-website.b-cdn.net",
    "ppl-ai-file-upload.s3.amazonaws.com",
    "pplx-res.cloudinary.com",
    "copilot-proxy.githubusercontent.com",
    "copilot-workspace.githubnext.com",
    "copilotprodattachments.blob.core.windows.net",
    "sydney.bing.com",
    "gateway.bingviz.microsoft.net",
    "gateway.bingviz.microsoftapp.net",
    "odc.officeapps.live.com",
    "location.microsoft.com",
    "anysphere-binaries.s3.us-east-1.amazonaws.com",
    "download.todesktop.com",
}

EXTRA = {
    "cursor": [
        "api2.cursor.sh", "api3.cursor.sh", "api4.cursor.sh", "api5.cursor.sh",
        "repo42.cursor.sh", "adminportal42.cursor.sh",
        "us-asia.gcpp.cursor.sh", "us-eu.gcpp.cursor.sh", "us-only.gcpp.cursor.sh",
        "authenticate.cursor.sh", "authenticator.cursor.sh",
        "authentication.cursor.sh", "prod.authentication.cursor.sh",
        "marketplace.cursorapi.com", "downloads.cursor.com",
        "agent.api5.cursor.sh", "agentn.api5.cursor.sh",
        "agent.us.api5.cursor.sh", "agentn.us.api5.cursor.sh",
        "agent.global.api5.cursor.sh", "agentn.global.api5.cursor.sh",
    ],
    "openai": [
        "api.openai.com", "platform.openai.com", "auth.openai.com",
        "cdn.openai.com", "chat.openai.com", "ab.chatgpt.com",
        "android.chat.openai.com", "ios.chat.openai.com",
        "files.oaiusercontent.com", "status.openai.com",
        "openai.com", "chatgpt.com", "sora.com", "www.chatgpt.com",
    ],
    "anthropic": [
        "api.anthropic.com", "console.anthropic.com", "claude.ai",
        "www.claude.ai", "platform.claude.com", "code.claude.com",
        "mcp.anthropic.com", "statsig.anthropic.com", "cdn.anthropic.com",
    ],
    "google-ai": [
        "generativelanguage.googleapis.com", "gemini.google.com",
        "aistudio.google.com", "ai.google.dev", "notebooklm.google.com",
        "bard.google.com", "makersuite.google.com",
    ],
    "xai": [
        "api.x.ai", "console.x.ai", "grok.x.ai", "grok.com", "x.ai",
    ],
    "microsoft-ai": [
        "copilot.microsoft.com", "www.copilot.microsoft.com",
        "sydney.bing.com", "edgeservices.bing.com",
        "api.cognitive.microsoft.com", "githubcopilot.com",
        "api.githubcopilot.com", "copilot-proxy.githubusercontent.com",
    ],
}

CN_AI = {
    "deepseek": [
        "deepseek.com", "www.deepseek.com", "chat.deepseek.com",
        "api.deepseek.com", "platform.deepseek.com", "coder.deepseek.com",
    ],
    "moonshot": [
        "moonshot.cn", "www.moonshot.cn", "kimi.moonshot.cn",
        "api.moonshot.cn", "platform.moonshot.cn", "kimi.com", "www.kimi.com",
    ],
    "zhipu": [
        "zhipuai.cn", "www.zhipuai.cn", "open.bigmodel.cn", "chatglm.cn",
        "www.chatglm.cn", "bigmodel.cn",
    ],
    "alibaba-ai": [
        "tongyi.aliyun.com", "dashscope.aliyuncs.com", "qianwen.aliyun.com",
        "bailian.console.aliyun.com", "dashscope.console.aliyun.com",
    ],
    "bytedance-cn": [
        "doubao.com", "www.doubao.com", "www.volcengine.com",
        "ark.cn-beijing.volces.com", "maas-api.ml-platform-cn-beijing.volces.com",
    ],
    "minimax": [
        "minimaxi.com", "www.minimaxi.com", "api.minimax.chat", "minimax.chat",
    ],
    "baichuan": [
        "baichuan-ai.com", "www.baichuan-ai.com", "api.baichuan-ai.com",
    ],
    "stepfun": [
        "stepfun.com", "www.stepfun.com", "yuewen.cn", "platform.stepfun.com",
    ],
    "yi": [
        "01.ai", "www.01.ai", "api.lingyiwanwu.com", "platform.lingyiwanwu.com",
    ],
    "siliconflow": [
        "siliconflow.cn", "www.siliconflow.cn", "api.siliconflow.cn",
        "cloud.siliconflow.cn",
    ],
    "tencent-ai": [
        "hunyuan.tencent.com", "yuanbao.tencent.com", "lke.cloud.tencent.com",
    ],
    "baidu-ai": [
        "yiyan.baidu.com", "qianfan.cloud.baidu.com", "aip.baidubce.com",
    ],
    "senseagora": [
        "sensetime.com", "nova.sensetime.com", "sensechat.sensetime.com",
    ],
}

domain_re = re.compile(r"^(DOMAIN|DOMAIN-SUFFIX),([^,\s#]+)", re.I)
cidr_re = re.compile(r"^IP-CIDR,([^,\s#]+)", re.I)


def ensure_repo(repo: Path) -> None:
    if (repo / ".git").is_dir() and (repo / "rules" / "surge").is_dir():
        subprocess.run(["git", "-C", str(repo), "pull", "--ff-only"], check=False)
        return
    repo.parent.mkdir(parents=True, exist_ok=True)
    if repo.exists():
        subprocess.run(["rm", "-rf", str(repo)], check=True)
    subprocess.run(["git", "clone", "--depth", "1", UPSTREAM, str(repo)], check=True)


def parse_list(text: str) -> tuple[list[str], list[str], list[str]]:
    section = "core"
    core: list[str] = []
    third: list[str] = []
    cidrs: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("# third"):
            section = "third"
            continue
        if low.startswith("# network"):
            section = "network"
            continue
        if low.startswith("# core"):
            section = "core"
            continue
        if line.startswith("#"):
            continue
        m = domain_re.match(line)
        if m:
            host = m.group(2).strip(".").lower()
            (third if section == "third" else core).append(host)
            continue
        m = cidr_re.match(line)
        if m and ":" not in m.group(1) and section in ("network", "core"):
            cidrs.append(m.group(1))
    return core, third, cidrs


def is_generic(host: str) -> bool:
    h = host.lower().rstrip(".")
    if h in HARD_DENY:
        return True
    if h in THIRD_PARTY_ALLOW_EXACT:
        return False
    if h in GENERIC_SUFFIX_DENY:
        return True
    for g in GENERIC_SUFFIX_DENY:
        if h == g or h.endswith("." + g):
            brand = (
                "openai", "anthropic", "claude", "chatgpt", "cursor", "perplexity",
                "pplx", "copilot", "gemini", "grok", "mistral", "cohere", "huggingface",
                "midjourney", "stability", "replicate", "groq", "openrouter", "oai",
            )
            return not any(b in h for b in brand)
    return False


def uniq_domains(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        x = x.strip().lower().rstrip(".")
        if not x or x in seen or x in HARD_DENY:
            continue
        if "*" in x or "/" in x or " " in x:
            continue
        if is_generic(x) and x not in THIRD_PARTY_ALLOW_EXACT:
            continue
        seen.add(x)
        out.append(x)
    return sorted(out)


def uniq_cidrs(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        x = x.strip()
        if not x or x in seen or ":" in x:
            continue
        seen.add(x)
        out.append(x)
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    ap.add_argument("--skip-clone", action="store_true")
    args = ap.parse_args()

    if not args.skip_clone:
        ensure_repo(args.repo)

    src = args.repo / "rules" / "surge"
    if not src.is_dir():
        print(f"missing {src}", file=sys.stderr)
        return 1

    out_dir = ROOT / "domains"
    patch_dir = ROOT / "patches"
    out_dir.mkdir(parents=True, exist_ok=True)
    patch_dir.mkdir(parents=True, exist_ok=True)

    for p in out_dir.glob("*.txt"):
        p.unlink()
    for p in patch_dir.glob("*-network.txt"):
        p.unlink()

    providers: dict[str, dict] = {}

    for path in sorted(src.glob("*.list")):
        key = path.stem
        if key in SKIP_LISTS:
            continue
        out_name = FILE_MAP.get(key, key)
        core, third, cidrs = parse_list(path.read_text(encoding="utf-8", errors="replace"))
        domains = list(core)
        for h in third:
            if h in THIRD_PARTY_ALLOW_EXACT or not is_generic(h):
                domains.append(h)
        domains.extend(EXTRA.get(out_name, []))
        domains = uniq_domains(domains)
        slot = providers.setdefault(out_name, {"domains": [], "cidrs": [], "sources": []})
        slot["sources"].append(key)
        slot["domains"] = uniq_domains(slot["domains"] + domains)
        slot["cidrs"] = uniq_cidrs(slot["cidrs"] + cidrs)

    for name, domains in CN_AI.items():
        providers[name] = {"domains": uniq_domains(domains), "cidrs": [], "sources": ["manual-cn"]}

    for name, meta in sorted(providers.items()):
        domains = meta["domains"]
        header = [
            f"# {name} — AI destination hostnames for DNS resolve",
            f"# sources: {', '.join(meta['sources'])} (+extras); filtered broad third-party SaaS",
            f"# upstream: https://github.com/VPSDance/ai-proxy-rules",
            f"# count: {len(domains)}",
            "",
        ]
        (out_dir / f"{name}.txt").write_text("\n".join(header + domains) + "\n", encoding="utf-8")
        if meta["cidrs"]:
            (patch_dir / f"{name}-network.txt").write_text(
                "\n".join([
                    f"# {name} published/network IPv4 from ai-proxy-rules",
                    f"# count: {len(meta['cidrs'])}",
                    "",
                ] + meta["cidrs"]) + "\n",
                encoding="utf-8",
            )

    lists: dict = {}
    for name, meta in sorted(providers.items()):
        sources: list[dict] = []
        if name == "google-ai":
            sources.append({
                "type": "text_url",
                "id": "goog_ipv4_only",
                "url": "https://www.gstatic.com/ipranges/goog_ipv4_only.txt",
                "note": "Official Google IPv4-only list; broad",
            })
        if name == "anthropic":
            sources.append({
                "type": "static_file",
                "id": "anthropic_inbound_docs",
                "path": "patches/anthropic-inbound.txt",
            })
        patch = patch_dir / f"{name}-network.txt"
        if patch.exists():
            sources.append({
                "type": "static_file",
                "id": f"{name}_network_cidrs",
                "path": f"patches/{name}-network.txt",
            })
        sources.append({
            "type": "resolve",
            "id": f"{name}_domains",
            "domains_file": f"domains/{name}.txt",
        })
        lists[name] = {
            "description": f"{name} AI destinations",
            "include_in_all": True,
            "sources": sources,
        }

    cfg = {
        "lists": lists,
        "egress_lists": {
            "openai-egress": {
                "description": "OpenAI published outbound ranges (connectors / agents / crawlers)",
                "sources": [
                    {"type": "openai_json", "id": "chatgpt_connectors", "url": "https://openai.com/chatgpt-connectors.json"},
                    {"type": "openai_json", "id": "chatgpt_agents", "url": "https://openai.com/chatgpt-agents.json"},
                    {"type": "openai_json", "id": "gptbot", "url": "https://openai.com/gptbot.json"},
                    {"type": "openai_json", "id": "searchbot", "url": "https://openai.com/searchbot.json"},
                    {"type": "openai_json", "id": "chatgpt_user", "url": "https://openai.com/chatgpt-user.json"},
                ],
            }
        },
        "resolve": {
            "resolvers": ["1.1.1.1", "8.8.8.8", "9.9.9.9"],
            "timeout_sec": 5,
            "retries": 2,
        },
    }
    (ROOT / "config" / "sources.json").write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    total = sum(len(m["domains"]) for m in providers.values())
    print(f"providers={len(providers)} domain_entries={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
