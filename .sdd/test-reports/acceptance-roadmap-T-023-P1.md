# 用户验收清单：roadmap-T-023 热点工具丰富度（P1–P3）

**版本**：开发完成后首测  
**前置**：后端 `8099`、前端 `5199`，`VITE_USE_MOCK=false`

---

## P1 — 公告自动解析

| # | 操作 | 通过标准 |
|---|------|----------|
| 1.1 | 问「机器人板块最近为什么火」 | Trace `tool_call` → `hotspot_fact_lookup` 含 `facts` 快讯；`stock_codes` 可为空 |
| 1.2 | 问「300308 所属概念最近为什么活跃」 | Trace `hotspot_fact_lookup.stock_codes` 含 `300308`；`facts` 含 `kind=announcement` 或明确无公告 |
| 1.3 | slots 带 `stock_code` 的热点问题 | 无需 LLM 填 `tool_params.stock_codes` 也能拉巨潮公告 |

## P2 — 动态 tool_names

| # | 操作 | 通过标准 |
|---|------|----------|
| 2.1 | 问「机器人板块最近为什么火」 | `tool_names` 含 `hotspot_fact_lookup` + `hotspot_signal_lookup`（近期口径） |
| 2.2 | 问「帮我复盘 4 月到 6 月半导体热点」 | `tool_names` **不含** `hotspot_signal_lookup`；含 `hotspot_fact_lookup` |
| 2.3 | 问「宠物行业逻辑 + 最近市场热度」 | 含 `market_ranking_lookup`（可选 `sector_heatmap_lookup`） |

## P3 — 多月份 RAG

| # | 操作 | 通过标准 |
|---|------|----------|
| 3.1 | 问「帮我复盘 4 月到 6 月半导体热点」 | Trace `rag_retrieval` 命中多个 `time_period`（如 2026-04/05/06）或正文声明证据不足 |
| 3.2 | 问「5 月机器人板块月度复盘」 | `retrieval_config.strategy=hotspot_dual`；RAG 含 `hotspots/` 月报片段 |

## 用户门禁话术

验收通过后回复：**「热点 P1 验收通过」** 或指出未通过条目编号。
