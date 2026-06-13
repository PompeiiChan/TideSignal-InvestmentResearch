# T-011b 热点助手 Response 验收清单

> 版本：V1.1 热点链路（RAG 双路 + 同花顺信号 + 东财快讯/巨潮公告 + 成色三段式）
> 验收方式：重启后端 → 新建会话 → 逐条提问 → 勾选

## 前置条件

- [ ] `LANGGRAPH_ENV=local`，后端 8099 已重启
- [ ] LLM / Embedding / Rerank 已配置（或接受 BM25 降级）
- [ ] 知识库已索引（`hotspots/`、`industry-reports/` 有内容）

## A. 链路结构（Trace 可观测）

| # | 检查项 | 通过标准 |
|---|--------|----------|
| A1 | 意图路由 | `hotspot_analysis` → `hotspot_agent` |
| A2 | RAG 双路 | `rag_retrieval` 策略 `hotspot_dual`，命中含 `hotspots/` 或 `industry-reports/` |
| A3 | 工具双调用 | `tool_call` 含 `hotspot_signal_lookup` + `hotspot_fact_lookup` |
| A4 | 证据合并 | `evidence_pack` 含 `tool_result` 两工具结果 + `retrieved_chunks` |

## B. Response 内容（正文）

| # | 检查项 | 通过标准 |
|---|--------|----------|
| B1 | 背景归因 | 能解释「为什么在炒 / 定价什么」，非纯报榜 |
| B2 | 时间口径 | 写明月报 `time_period` 和/或当日 `trade_date` |
| B3 | **### 事实支撑** | 有可核验政策/公告/月报 citation 或明确写「未见硬事实」 |
| B4 | **### 预期博弈** | 区分市场预期与已发生事实，标注不确定性 |
| B5 | **### 纯叙事风险** | 指出概念炒作/拥挤/兑现风险，不写买卖建议 |
| B6 | 引用规范 | 文末 `### 参考来源`，RAG 用 `[citation:N]`，同源合并 |
| B7 | 风险提示 | 参考来源后单独一段合规风险提示 |
| B8 | 禁止项 | 无目标价、无买入卖出推荐、无「必涨」 |

## C. 推荐验收问法

1. **「机器人板块最近有哪些政策催化？利好是实打实的还是纯概念？」**
   - 期望：RAG 机械/热点月报 + 事实快讯 + reason 标签 + 成色三段

2. **「4 月 AI 算力为什么成为主线？有没有业绩支撑？」**
   - 期望：命中 `2026-04-market-hotspots`，解释边界，三段式成色

3. **「今天市场什么题材比较热？」**
   - 期望：同花顺 `reason` 标签 + 月报背景，不编造涨跌幅

## D. 降级场景

| # | 场景 | 通过标准 |
|---|------|----------|
| D1 | 同花顺不可用 | `signal_mode=kb_material`，标注时效滞后，仍有三段式 |
| D2 | 快讯/公告不可用 | `hotspot_fact_lookup.fallback_used=true`，正文说明事实层缺失 |
| D3 | RAG 零命中 | 写「本地热点资料不足」，不编造政策细节 |

## E. 自动化门禁

```bash
cd backend && PYTHONPATH=.. ../.venv/bin/python -m pytest tests/test_hotspot_acceptance.py -q
```

通过 ≠ 全文质量验收；**B 组须人工读 Response 勾选**。
