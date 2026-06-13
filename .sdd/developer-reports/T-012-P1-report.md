# T-012 Phase 1 完成报告

> **任务**：T-012 LangGraph 真实编排 — Phase 1 基础设施与状态机骨架  
> **完成时间**：2026-06-12

## 交付摘要

- 根 `pyproject.toml` 新增 `langgraph>=0.2.0`、`langchain-core>=0.3.0`，已安装至项目 `.venv`
- 新建 `backend/src/integrations/langgraph/`：`state.py`、`graph.py`、`routing.py`、`runner.py`、`trace_recorder.py`、`__init__.py`
- 新建 `backend/src/agents/nodes/`：16 个节点 stub（ID 对齐 `langgraph-flow.md`）
- `TraceService.create_langgraph_trace()` 接收 recorder steps 落库
- `ConfigStatusRead.orchestration` + `ConfigStatusService._langgraph_status()`
- `integrations/llm/prompts/` 拆分：`intent.py` 去除 calculator，新增 `prediction_request` 说明；`prompts/__init__.py` 保持 LLMService 向后兼容
- **未修改** `chat_service.py`（Phase 4 接入）

## 新增文件

```
backend/src/integrations/langgraph/__init__.py
backend/src/integrations/langgraph/state.py
backend/src/integrations/langgraph/graph.py
backend/src/integrations/langgraph/routing.py
backend/src/integrations/langgraph/runner.py
backend/src/integrations/langgraph/trace_recorder.py
backend/src/agents/__init__.py
backend/src/agents/nodes/__init__.py
backend/src/agents/nodes/context_preprocess.py
backend/src/agents/nodes/intent_recognition.py
backend/src/agents/nodes/slot_extraction.py
backend/src/agents/nodes/clarification_check.py
backend/src/agents/nodes/clarification_response.py
backend/src/agents/nodes/routing_decision.py
backend/src/agents/nodes/hotspot_agent.py
backend/src/agents/nodes/data_query_agent.py
backend/src/agents/nodes/stock_analysis_agent.py
backend/src/agents/nodes/document_qa_agent.py
backend/src/agents/nodes/tool_call.py
backend/src/agents/nodes/rag_retrieval.py
backend/src/agents/nodes/evidence_merge.py
backend/src/agents/nodes/quality_check.py
backend/src/agents/nodes/response_assembly.py
backend/src/agents/nodes/fallback_response.py
backend/src/integrations/llm/prompts/__init__.py
backend/src/integrations/llm/prompts/_shared.py
backend/src/integrations/llm/prompts/intent.py
backend/tests/test_langgraph_graph.py
backend/tests/test_langgraph_trace.py
```

## 修改文件

```
pyproject.toml
backend/src/models/config_status.py
backend/src/services/config_status_service.py
backend/src/services/trace_service.py
backend/tests/test_health.py
```

## 删除文件

```
backend/src/integrations/llm/prompts.py  → 由 prompts/ 包替代
```

## 质量门禁

| 检查 | 结果 |
|------|------|
| `ruff check backend/src backend/tests` | PASS |
| `mypy backend/src backend/tests` | PASS |
| `pytest backend/tests` | **64 passed**, 8 skipped |

## 单测覆盖（Phase 1）

- `test_langgraph_graph.py`：`build_graph()` 可 compile；`is_langgraph_enabled` 仅 `LANGGRAPH_ENV=local` 为 True
- `test_langgraph_trace.py`：`create_langgraph_trace` 写入 `context_preprocess` step；intent prompt 无 calculator、含 prediction_request
- `test_health.py`：`GET /api/config/status` 含 `orchestration` 字段

**本 Phase 已完成，等待 Orchestrator 调度 Tester 验证。**
