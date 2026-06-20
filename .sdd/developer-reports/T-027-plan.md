# T-027 问股 citation 区瘦身（assembly compact）— 技术方案

> **任务 ID**：T-027  
> **依赖**：T-025  
> **动机**：T-025 后 `stock_full` 联调 `citation_context_chars≈23031`，RAG 全文 snippet + 估值历史全量 JSON 是主要膨胀源。

## 目标

- 问股 `stock_full` / `stock_narrative` / `compound` profile 使用 **compact citation context**，显著降低 assembly prefill 字符数。
- 不改 LangGraph 拓扑；保留多期财务表、估值分位、机构预期、研报元数据、RAG 引用编号等 **citation 质量**（BC-006 不退化）。

## 实现

### 1. `citation_context_compact.py`

- `dump_citation_json`：compact 模式无 indent、紧凑 separators。
- `slim_financial_periods` / `slim_valuation_history` / `slim_api_facts` / `slim_research_reports`。
- `truncate_snippet`（480 字符）+ `rag_hits_for_assembly`（最多 6 条）。

### 2. `format_citation_context(..., compact=False)`

- compact 时省略 `time_ctx.prompt_block()`（system prompt 已有权威时间）。
- 工具 JSON 走 slim + compact dump；RAG 片段截断。

### 3. `profile.use_compact_citation_context`

- 启用 profile：`STOCK_FULL`、`STOCK_NARRATIVE`、`COMPOUND`。
- `response_assembly` 传入 `compact=`，Trace `prompt_stats.citation_context_mode`。

## 验收

| AC | 标准 |
|----|------|
| 1 | `stock_full` assembly Trace 含 `citation_context_mode=compact` |
| 2 | compact 相对 full 字符数下降 ≥30%（合成 payload 单测 ≥30%） |
| 3 | compact 仍含「多期结构化财务数据」「估值历史分位」等关键节 |
| 4 | RAG snippet 单条 ≤480 字符 |
| 5 | `data_default` / `hotspot_default` 仍用 full 模式 |

## 文件

- 新增：`backend/src/services/citation_context_compact.py`
- 修改：`citation_catalog.py`、`profile.py`、`response_assembly.py`
- 测试：`backend/tests/test_citation_context_compact.py`
