# 测试报告：T-027 问股 citation 区瘦身（assembly compact）

**测试时间**：2026-06-20  
**Tester Agent ID**：cursor-tester

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | `stock_full` assembly Trace 含 `citation_context_mode=compact` | PASS | `response_assembly.py:398-404` 写入 `prompt_stats.citation_context_mode`；`profile.use_compact_citation_context(STOCK_FULL)` 为 True（`test_citation_context_compact.py:35-40`）。 |
| 2 | compact 相对 full 字符数显著下降 | PASS | `test_compact_reduces_char_count_for_stock_payload`：`len(compact) < len(full) * 0.7`（降 ≥30%）。 |
| 3 | compact 仍保留多期财务、估值分位等关键节 | PASS | 同测断言含「多期结构化财务数据」「估值历史分位」「API 公告与资讯」。 |
| 4 | RAG snippet 截断 | PASS | `truncate_snippet` ≤480 字符；`test_compact_truncates_rag_snippets` 长 snippet 不出现在 compact 输出。 |
| 5 | 非问股 profile 不用 compact | PASS | `DATA_DEFAULT`、`HOTSPOT_DEFAULT` → `use_compact_citation_context` 为 False。 |

## 技术检查

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | ruff check 变更文件 | PASS | `backend/.venv/bin/python -m ruff check src/services/citation_context_compact.py src/services/citation_catalog.py src/agents/assembly/profile.py src/agents/nodes/response_assembly.py tests/test_citation_context_compact.py -q` → exit 0 |
| 2 | pytest 新增 + 回归 | PASS | `test_citation_context_compact.py` + `test_citation_catalog.py` + `test_response_assembly_streaming.py` → **24 passed** |
| 3 | compact 省略重复时间块 | PASS | `test_compact_omits_time_block`：full 含「系统时间」，compact 不含。 |
| 4 | 估值历史 slim | PASS | `test_compact_slims_valuation_history`：quarterly_series 限 4 点，剔除 trading_day_count/notes。 |

## 代码核查摘要

| 项 | 结果 | 位置 |
|----|------|------|
| compact 模块 | PASS | `backend/src/services/citation_context_compact.py` |
| format_citation_context compact 分支 | PASS | `backend/src/services/citation_catalog.py:542+` |
| profile 分级 | PASS | `backend/src/agents/assembly/profile.py:128-139` |
| assembly 接入 + Trace | PASS | `backend/src/agents/nodes/response_assembly.py:376-404` |
| 无密钥/TODO 泄露 | PASS | 变更文件抽检通过 |

## 命令输出摘录

```text
$ backend/.venv/bin/python -m pytest backend/tests/test_citation_context_compact.py backend/tests/test_citation_catalog.py backend/tests/test_response_assembly_streaming.py -q
24 passed, 6 warnings in 0.38s
```

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 建议 |
|---|------|------|
| 1 | 未跑 live 问股「宁德时代 2026 一季报」全链路 Trace 绝对字符对比 | 用户门禁时在真实环境核对 `prompt_stats.citation_context_chars` 相对 T-025 baseline（≈23k）降幅 |
