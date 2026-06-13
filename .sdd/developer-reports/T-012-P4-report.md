# T-012 Phase 4 — Developer Report

> **任务**：Chat 接入、门禁、回归  
> **完成日期**：2026-06-12  
> **状态**：待 Tester 验证

---

## 交付摘要

1. **`LangGraphRunner.run_stream()`**：`astream(stream_mode="values")` 驱动图执行；`stream_callback` 队列推送 `content_delta` / `content_done` / `rich_blocks`；节点相位映射 `thinking` / `indexing` / `retrieving` / `generating` / `quality_check`；结束后持久化 assistant 消息、`create_langgraph_trace()`、append `END` step、`done` 事件含 `ChatQueryResponse`。
2. **`chat_service._stream_assistant_reply`**：仅 LangGraph 路径；`LANGGRAPH_ENV!=local` → 503；删除线性 `recognize_intent→rag→stream→quality→create_llm_trace`；`regenerate_stream` 复用同一路径。
3. **Trace**：`create_langgraph_trace` metadata 含 `langgraph_connected: true`；`routing_decision` 输出 `langgraph_connected: true`。
4. **配置与文档**：`backend/.env.example`、`docs/startup.md` 增加 LangGraph 说明。
5. **测试**：新增 `test_langgraph_chat.py`；`conftest` autouse mock `is_langgraph_enabled` + LangGraph LLM 客户端；更新 trace 节点 ID 断言。

---

## 修改文件

| 文件 | 变更 |
|------|------|
| `backend/src/integrations/langgraph/runner.py` | 新增 `run_stream()` |
| `backend/src/services/chat_service.py` | 仅 LangGraph 编排 |
| `backend/src/services/trace_service.py` | metadata `langgraph_connected` |
| `backend/src/agents/nodes/routing_decision.py` | 输出 `langgraph_connected: true` |
| `backend/tests/conftest.py` | LangGraph mock + 门禁 |
| `backend/tests/test_langgraph_chat.py` | 新增 |
| `backend/tests/test_sessions_layout.py` | LangGraph trace 断言 |
| `backend/tests/test_api_regression.py` | `intent_recognition` 节点 |
| `backend/.env.example` | `LANGGRAPH_ENV=local` 说明 |
| `docs/startup.md` | LangGraph 启动说明 |
| `.sdd/experience.md` | P4 经验 |

---

## 质量门禁

| 检查 | 结果 |
|------|------|
| `ruff check backend/src backend/tests` | PASS |
| `mypy backend/src backend/tests` | PASS |
| `pytest backend/tests` | **107 passed**, 8 skipped |

---

## 用户操作说明

1. 在 `backend/.env` 增加（若尚未配置）：

```env
LANGGRAPH_ENV=local
```

2. 确保 `LLM_INTENT_*` 与 `LLM_*` 已配置（Chat 503 门禁同时检查 LLM）。
3. **重启后端**（8099）使环境变量生效。
4. 验证：`GET /api/config/status` → `data.orchestration.status === "ready"`；管理端 Trace 时间线节点 ID 为 `context_preprocess` 等 langgraph-flow ID。

---

**本 Phase 已完成，等待 Orchestrator 调度 Tester 验证。**
