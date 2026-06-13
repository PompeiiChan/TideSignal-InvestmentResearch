# T-012 Phase 3 开发报告 — 执行链路

> **任务**：T-012 Phase 3  
> **日期**：2026-06-12  
> **状态**：待 Tester 验收

---

## 交付摘要

实现 LangGraph 执行链路：4 个子 Agent → 并行 RAG/Tool → evidence_merge → quality_check → response_assembly / fallback_response。mock LLM 下问数/问股/热点/兜底全路径可走通。

**未改动**：`chat_service.py`（留 Phase 4）。

---

## 修改/新增文件

### 子 Agent 节点
- `backend/src/agents/nodes/hotspot_agent.py`
- `backend/src/agents/nodes/data_query_agent.py`
- `backend/src/agents/nodes/stock_analysis_agent.py`
- `backend/src/agents/nodes/document_qa_agent.py`

### 执行节点
- `backend/src/agents/nodes/tool_call.py`
- `backend/src/agents/nodes/rag_retrieval.py`
- `backend/src/agents/nodes/evidence_merge.py`
- `backend/src/agents/nodes/quality_check.py`
- `backend/src/agents/nodes/response_assembly.py`
- `backend/src/agents/nodes/fallback_response.py`
- `backend/src/agents/nodes/_helpers.py`（`build_parallel_trace_update`、`response_kind_for_intent`）
- `backend/src/agents/nodes/routing_decision.py`（`local_return_calculator` 槽位检测）

### 工具层
- `backend/src/agents/tools/__init__.py`
- `backend/src/agents/tools/mock_market_ranking_lookup.py`
- `backend/src/agents/tools/mock_financial_profile_lookup.py`
- `backend/src/agents/tools/mock_hotspot_material_lookup.py`
- `backend/src/agents/tools/return_calculator.py`

### Prompt
- `backend/src/integrations/llm/prompts/agents/hotspot.py`
- `backend/src/integrations/llm/prompts/agents/data_query.py`
- `backend/src/integrations/llm/prompts/agents/stock_analysis.py`
- `backend/src/integrations/llm/prompts/agents/document_qa.py`
- `backend/src/integrations/llm/prompts/assembly.py`
- `backend/src/integrations/llm/prompts/fallback.py`

### Runner
- `backend/src/integrations/langgraph/runner.py`（`ainvoke` 末尾 append `END` trace step）

### 测试
- `backend/tests/test_langgraph_execution.py`

### 经验
- `.sdd/experience.md`（T-012 P3 条目）

---

## 质量门禁

| 检查项 | 结果 |
|--------|------|
| `ruff check backend/src backend/tests` | PASS |
| `mypy backend/src backend/tests` | PASS |
| `pytest backend/tests` | **105 passed**, 8 skipped |

---

## Phase 3 验收对照

| 验收项 | 状态 |
|--------|------|
| 4 个子 Agent 真实实现 + agent prompts | ✅ |
| `agents/tools/*` + `tool_call` 调度 | ✅ |
| `rag_retrieval` 调 `RagService.retrieve()`，Trace 含 rerank_before/after | ✅ |
| `evidence_merge` 合并 tool + rag + agent | ✅ |
| `quality_check` 适配 `LLMService.quality_check`，映射 pass/revise/reject | ✅ |
| `response_assembly` 流式 + `enrich_rich_blocks`，数字来自 tool_result | ✅ |
| `fallback_response` 预测/质检 reject/工具失败兜底 | ✅ |
| `fanout_after_agent` Send 并行 rag+tool | ✅（图已有，节点已实现） |
| quality reject → fallback_response | ✅ |
| Runner append END trace step | ✅ |
| `test_langgraph_execution.py` 全路径单测 | ✅ |
| 未改 chat_service | ✅ |

---

**本 Phase 已完成，等待 Orchestrator 调度 Tester 验证。**
