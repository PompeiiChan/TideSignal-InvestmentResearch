# T-012 Phase 2 开发报告 — 前置链路

> **任务**：T-012 LangGraph 真实编排  
> **阶段**：Phase 2 — 预处理 → 澄清 / 路由  
> **完成日期**：2026-06-12

---

## 1. 交付摘要

实现 `context_preprocess` → `intent_recognition` → `slot_extraction` → `clarification_check` → (`clarification_response` | `routing_decision`) 全链路真实逻辑；各节点通过 `TraceRecorder` 写入 `trace_steps`；`LangGraphRunner.ainvoke` 支持 `user_query` / `session_id` / `chat_history` 入参。

**未改动**：`chat_service.py`（留待 Phase 4）。

---

## 2. 修改/新增文件

| 文件 | 说明 |
|------|------|
| `backend/src/agents/nodes/_helpers.py` | 节点 Trace 记录、LLM JSON 调用与字段归一化 |
| `backend/src/agents/nodes/context_preprocess.py` | 清洗 query、history 摘要、system_context、risk_hint |
| `backend/src/agents/nodes/intent_recognition.py` | LLM 意图 JSON（`prompts/intent.py`） |
| `backend/src/agents/nodes/slot_extraction.py` | LLM 槽位 JSON（`prompts/slots.py`） |
| `backend/src/agents/nodes/clarification_check.py` | 纯规则澄清判断（§6.1） |
| `backend/src/agents/nodes/clarification_response.py` | LLM 结构化追问（`prompts/clarification.py`） |
| `backend/src/agents/nodes/routing_decision.py` | intent→route_target + execution_plan（§5.2） |
| `backend/src/integrations/llm/prompts/slots.py` | 槽位抽取 Prompt |
| `backend/src/integrations/llm/prompts/clarification.py` | 澄清追问 Prompt |
| `backend/src/integrations/langgraph/runner.py` | `ainvoke` 入参扩展 |
| `backend/src/integrations/langgraph/__init__.py` | 懒加载打破循环依赖 |
| `backend/src/agents/nodes/rag_retrieval.py` | 并行 fan-out 兼容 stub |
| `backend/src/agents/nodes/tool_call.py` | 并行 fan-out 兼容 stub |
| `backend/src/agents/nodes/stock_analysis_agent.py` | 最小 stub（current_node + agent_result） |
| `backend/tests/test_langgraph_preprocessing.py` | Phase 2 单测与集成测 |

---

## 3. 质量门禁

| 检查项 | 结果 |
|--------|------|
| `ruff check backend/src backend/tests` | PASS |
| `mypy backend/src backend/tests` | PASS |
| `pytest backend/tests` | **93 passed**, 8 skipped |

---

## 4. Phase 2 验收点对照

| 验收点 | 状态 |
|--------|------|
| 6 个前置节点真实逻辑 + Prompt | ✅ |
| `clarification_check` 4 种规则分支单测 | ✅（低置信 / 缺股 / 缺指标 / 歧义 / 时间默认可路由） |
| `routing_decision` 映射表单测 | ✅（hotspot/data/stock/document/prediction/fallback） |
| 每节点写 Trace step | ✅ |
| 模糊问题 → 终止于 `clarification_response` | ✅ 集成测 |
| 清晰问股 → `routing_decision` + `route_target=stock_analysis_agent` | ✅ 集成测 |
| 子 Agent 节点最小 stub，路由可达 | ✅ |
| 未改 `chat_service` | ✅ |
| Trace `steps[].node` 与 langgraph-flow.md 一致 | ✅ |

---

## 5. 实现要点

1. **澄清规则**：`intent_confidence < 0.70`、核心槽位缺失、`ambiguous_slots` 非空 → `need_clarification=True`；`time_range` 缺失且其他信息足够时仅写 `clarification_reason` 说明默认近一交易日。
2. **路由映射**：`prediction_request` / `chit_chat` / `unknown` → `fallback_response`；四类业务意图 → 对应 Agent；各 Agent 附带 §6.3 默认 `execution_plan`。
3. **Trace**：节点通过 `_helpers.run_node_with_trace` 追加 step，`trace_steps` 使用 `operator.add` reducer。
4. **并行 stub**：`rag_retrieval` / `tool_call` stub 不写 `current_node`，避免 LangGraph `Send` 并行更新冲突。

---

## 6. 待 Phase 3/4

- 子 Agent、RAG/Tool 真实执行、`response_assembly` / `fallback_response` 完整逻辑
- `chat_service` 切换 LangGraph Runner + SSE
- `END` 节点 Trace 落库

---

*本 Phase 已完成，等待 Orchestrator 调度 Tester 验证。*
