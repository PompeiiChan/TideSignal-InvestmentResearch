# T-017 多轮上下文注入下游节点 — Developer 完成报告

> **任务 ID**：T-017  
> **完成日期**：2026-06-19  
> **状态**：待 Tester 验证

---

## 实现摘要

1. 新增 `backend/src/services/conversation_context.py`：`build_conversation_context`、`format_conversation_context_for_prompt`、`enrich_state_conversation_context`。
2. `slot_extraction` 输出 `conversation_context` 与 trace 预览字段。
3. `stock_analysis_agent` 向 LLM payload 注入 `history_summary` / `active_slots` / `conversation_context`。
4. `evidence_merge` 将 `conversation_context` 与 `active_slots` 写入 `evidence_pack`；trace input 含 `has_conversation_context`。
5. `response_assembly` trace input 含多轮字段；有上下文时在 user prompt 追加 `【多轮对话上下文】` 块。
6. `rag_retrieval` trace input 含 `active_slots` / `stock_name`；短续问 + 继承 `stock_name` 时 `filter_hits_by_entity` 过滤。
7. Prompt 更新：`stock_analysis.py` §多轮续问、`assembly.py` ASSEMBLY_STOCK 多轮约束。
8. `state.py` 增加 `conversation_context` 字段。

## 测试

```bash
PYTHONPATH=. .venv/bin/python -m pytest \
  backend/tests/test_conversation_context.py \
  backend/tests/test_response_assembly_multiturn.py \
  backend/tests/test_stock_analysis_agent_multiturn.py \
  backend/tests/test_evidence_merge_context.py \
  backend/tests/test_slot_extraction_multiturn.py -q
```

结果：**9 passed**

## 验收映射

| AC | 实现 |
|----|------|
| 续问延续标的/时间口径 | `response_assembly` user prompt 多轮块 + assembly/stock prompt 约束 |
| Trace 含 history_summary / active_slots | `slot_extraction`、`response_assembly`、`stock_analysis_agent` trace input |
| 首轮无回归 | `has_context=false` 时不注入多轮块 |

## 修改文件

- `backend/src/services/conversation_context.py`（新增）
- `backend/src/integrations/langgraph/state.py`
- `backend/src/agents/nodes/slot_extraction.py`
- `backend/src/agents/nodes/stock_analysis_agent.py`
- `backend/src/agents/nodes/evidence_merge.py`
- `backend/src/agents/nodes/response_assembly.py`
- `backend/src/agents/nodes/rag_retrieval.py`
- `backend/src/integrations/llm/prompts/agents/stock_analysis.py`
- `backend/src/integrations/llm/prompts/assembly.py`
- `backend/tests/test_conversation_context.py`（新增）
- `backend/tests/test_response_assembly_multiturn.py`（新增）
- `backend/tests/test_stock_analysis_agent_multiturn.py`（新增）
- `backend/tests/test_evidence_merge_context.py`（新增）

**本功能已完成，等待 Orchestrator 调度 Tester 验证。**
