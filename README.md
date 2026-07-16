# ai-cidr-lists

收集并发布 **AI 服务相关 IPv4 CIDR**，供网关做目的地址分流（例如 qosnat2 `Alias.url` + `EgressPolicy` → WARP）。

## 产物

| 文件 | 用途 |
|------|------|
| `lists/all.txt` | 合并后的 **目的网段**（LAN 客户端访问 AI 服务） |
| `lists/google.txt` 等 | 按厂商拆分 |
| `lists/egress/*.txt` | 厂商 **出站** 网段（爬虫/connectors 访问你）；**不要**当作 LAN 目的分流 |

格式与 Google 官方列表、qosnat2 `FetchCIDRListFromURL` 一致：每行一个 IPv4 CIDR，`#` 为注释。

## 数据来源分层

1. **官方网段**：如 Google `goog_ipv4_only.txt`、Anthropic inbound docs  
2. **静态补丁**：`patches/`  
3. **域名解析**：`domains/*.txt` → A 记录 `/32`（OpenAI 等无官方 inbound 列表时的主手段）  
4. **厂商 egress JSON**：写入 `lists/egress/`，与目的列表隔离

> 注意：Google 列表较宽；CDN 共享 IP 可能误伤。OpenAI 公开的 JSON 多是 **egress**，不能替代 API 目的地址。

## 构建

```bash
PYTHONPATH=src python3 scripts/build.py
```

依赖：Python 3.10+ 标准库（无需 pip 包）。

## 给 qosnat2 用

1. 发布本仓库后，取 raw URL，例如：
   `https://raw.githubusercontent.com/hk59775634/ai-cidr-lists/main/lists/openai.txt`
2. 在 qosnat2 建 Alias：`url` 填上述地址，刷新 members  
3. EgressPolicy：`dst_alias` → `wan-warp`（或其它专用出口）

建议先按厂商挂多个 alias，确认无误后再用 `lists/all.txt`。

## 目录

```
config/sources.json   # 采集配置
domains/              # 待解析域名
patches/              # 手工/文档摘录 CIDR
src/ai_cidr_lists/    # 构建逻辑
lists/                # 生成物（可提交，便于 raw URL 消费）
meta/build.json       # 生成元数据与警告
```

## Related work（现成项目）

公开生态里**已有不少「AI 爬虫出站 IP」聚合**，用途是 WAF/robots 放行或拦截「AI → 你的站点」：

| 项目 | 侧重 |
|------|------|
| [sefinek/trusted-ips-whitelist](https://github.com/sefinek/trusted-ips-whitelist)（亦作 known-bots-ip-whitelist） | GPTBot / PerplexityBot 等官方 JSON 白名单 |
| [ipanalytics/CrawlerScope](https://github.com/ipanalytics/CrawlerScope) | 爬虫/监控类官方网段流水线 |
| [disposable/cloud-ip-ranges](https://github.com/disposable/cloud-ip-ranges) | 云厂商 + OpenAI crawler 等网段镜像 |
| [Listo-Labs-Ltd/mcp-ip-guard-python](https://github.com/Listo-Labs-Ltd/mcp-ip-guard-python) | MCP 侧 OpenAI/Anthropic **egress** allowlist |
| [sourcecidr.com](https://sourcecidr.com/) | 厂商网段目录（含 AI platforms） |

以上几乎都是 **vendor → your server（egress/crawler）**。

本仓库额外维护 **LAN 客户端 → AI 服务（destination）** 列表（官方 inbound + DNS resolve + Google 全量等），并与 `lists/egress/` 严格分开，避免拿爬虫网段去做出口分流。

## License

MIT。第三方 IP 数据仍受原发布方条款约束。
