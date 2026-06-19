# 测试报告：roadmap-T-023 热点工具丰富度（P1–P3）

**测试时间**：2026-06-15  
**Tester Agent ID**：主会话自动化  
**版本检查点**：`04e344e`

## 结果：PASS

## 验收标准逐条验证

### P1 — 公告自动解析

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1.1 | `resolve_hotspot_stock_codes` 从 query 内联 6 位代码解析 | PASS | `test_resolve_hotspot_stock_codes_from_query_and_slots` |
| 1.2 | `hotspot_fact_lookup` 调用 `resolve_hotspot_stock_codes` | PASS | `hotspot_fact_lookup.py` 返回 `stock_codes` 字段 |
| 1.3 | `hotspot_agent` 写入 `tool_params.stock_codes` | PASS | `hotspot_agent.py` 规划后合并解析结果 |
| 1.4 | `tool_call` 传递 `query`/`slots` 给 fact lookup | PASS | `tool_call.py` setdefault |

### P2 — 动态 tool_names

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 2.1 | 复盘类跳过 `hotspot_signal_lookup` | PASS | `test_resolve_hotspot_tools_skip_signal_for_replay` |
| 2.2 | 尊重 Agent `tool_names` 白名单 | PASS | `test_resolve_hotspot_tools_respects_agent_selection` |
| 2.3 | `build_hotspot_execution_plan` 复盘仅 fact | PASS | `test_hotspot_execution_plan_has_dual_tools_and_rag_strategy` 更新 |
| 2.4 | 近期问法仍含 signal | PASS | `test_routing_decision_hotspot_recent_query` api_primary |

### P3 — 多月份 RAG

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 3.1 | `extract_hotspot_month_keys` 解析「4月到6月」 | PASS | `test_extract_hotspot_month_keys_from_range` |
| 3.2 | execution_plan 写入 `hotspot_month_keys` | PASS | `test_build_hotspot_plan_multi_month_sets_retrieval_keys` |
| 3.3 | `diversify_hotspot_hits_by_month` 保留多月份 | PASS | `test_diversify_hotspot_hits_keeps_multiple_months` |
| 3.4 | `rag_retrieval` hotspot_dual 多路检索 | PASS | 代码路径 `retrieve_hotspot_multi_month` + `rag_retrieval.py` |

## 自动化测试汇总

```
cd backend && PYTHONPATH=.. ../.venv/bin/python -m pytest \
  tests/test_hotspot_tool_plan.py \
  tests/test_hotspot_recency.py \
  tests/test_hotspot_acceptance.py \
  tests/test_hotspot_rag_multi_month.py \
  tests/test_tool_call_stock_plan.py \
  tests/test_rag_time_period_diversify.py -q
23 passed
```

## 阻塞证据

无。完整对话 Trace（含 LLM 规划 `tool_names`）需用户门禁。

## 超出范围

| # | 问题 | 建议 |
|---|------|------|
| 1 | 公司名称→代码仅靠 KB/东财 suggest，无 KB 公司可能无公告 | 后续可扩展 alias 表 |
