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
2. **静态补丁**：`patches/`（含上游 Network 段 IPv4）  
3. **域名解析**：`domains/*.txt` → A 记录 `/32`  
4. **厂商 egress JSON**：写入 `lists/egress/`，与目的列表隔离  

域名列表主要同步自 [VPSDance/ai-proxy-rules](https://github.com/VPSDance/ai-proxy-rules)（按 provider 拆分），并补充 Cursor 官方白名单与国内 AI（DeepSeek / Kimi / 通义等）。已过滤过宽第三方（如整站 `auth0.com` / `stripe.com`）。

> 注意：Google 列表较宽；CDN 共享 IP 可能误伤。OpenAI 公开的 JSON 多是 **egress**，不能替代 API 目的地址。

## 构建

```bash
# 从上游刷新 domains/ + config/sources.json
python3 scripts/sync-domains-from-upstream.py

# 解析域名并生成 lists/*.txt
PYTHONPATH=src python3 scripts/build.py
```

依赖：Python 3.10+ 标准库（无需 pip 包）。

## 给 qosnat2 用

1. 取 raw URL，例如：
   `https://raw.githubusercontent.com/hk59775634/ai-cidr-lists/main/lists/openai.txt`
   或合并列表 `.../lists/all.txt`
2. 在 qosnat2 建 Alias：`url` 填上述地址，刷新 members  
   （也可用本机 FQDN 别名直接引用 `domains/*.txt` 中的域名）
3. EgressPolicy：`dst_alias` → `wan-warp`（或其它专用出口）

## 目录

```
config/sources.json                      # 采集配置
domains/*.txt                            # 按厂商待解析域名（约 90+ 家）
patches/                                 # 手工/文档/上游 Network CIDR
scripts/sync-domains-from-upstream.py    # 同步域名
scripts/build.py                         # 生成 lists/
lists/                                   # 发布产物
meta/build.json                          # 元数据与解析警告
```

## Related work

| 项目 | 侧重 |
|------|------|
| [VPSDance/ai-proxy-rules](https://github.com/VPSDance/ai-proxy-rules) | AI **域名**分流规则（本仓库 domains 主要上游） |
| [sefinek/trusted-ips-whitelist](https://github.com/sefinek/trusted-ips-whitelist) | GPTBot 等爬虫 **egress** 白名单 |
| [ipanalytics/CrawlerScope](https://github.com/ipanalytics/CrawlerScope) | 爬虫/监控网段流水线 |
| [sourcecidr.com](https://sourcecidr.com/) | 厂商网段目录 |

本仓库面向 **LAN → AI 目的网段**，与爬虫 egress 列表严格分开。

## License

MIT。第三方 IP 数据仍受原发布方条款约束。
