# T-016 完成报告：会话 pending_slots 多轮闭环（F19）

> **任务 ID**：T-016  
> **状态**：开发完成，待 Tester 验收  
> **完成日期**：2026-06-19

---

## 实现摘要

1. **`backend/src/services/slot_memory.py`**：单一配置源 `INHERITABLE_SLOTS_BY_INTENT`、`REQUIRED_SLOTS_BY_INTENT`；`merge_pending_slots`、`filter_missing_after_inherit`、`build_context_state_from_run`、`should_clear_pending`、`should_persist_pending`。
2. **`SessionRecord.context_state`** JSON 字段 + `ensure_schema_columns()` SQLite ALTER 迁移（`init_db` 末尾调用）。
3. **`LangGraphRunner.run_stream`**：启动时从 `session.context_state` 注入 `pending_slots`；成功路由后持久化，澄清轮不覆盖 pending，`chit_chat` 等意图清空。
4. **`AgentState`** 扩展 `pending_slots`、`pending_intent_id`、`inherited_slot_keys`、`active_slots` 等。
5. **`slot_extraction`**：合并 pending + history_summary 入 LLM payload；trace 输出 `extracted_slots` / `pending_slots` / `inherited_slot_keys`。
6. **`clarification_check`**：引用 `REQUIRED_SLOTS_BY_INTENT`；已继承槽位不计 missing。
7. **`context_preprocess`**：`context_pack` 含 `pending_slots`。
8. **`slots.py`**：多轮 pending_slots few-shot 规则。
9. **`SessionRepository.update_context_state`**。

## Bad Case 修复

- **BC-008**：「宁德时代基本面怎么样」→「一季报呢」不再因缺失 `stock_name` 触发澄清。

## 测试

```bash
PYTHONPATH=. .venv/bin/python -m pytest \
  backend/tests/test_slot_memory.py \
  backend/tests/test_slot_extraction_multiturn.py \
  backend/tests/test_clarification_inherited.py \
  backend/tests/test_short_term_memory.py \
  backend/tests/test_langgraph_preprocessing.py -q
```

结果：48 passed（T-016 新增 10 + 回归 38）。

```bash
PYTHONPATH=. .venv/bin/python -m ruff check \
  backend/src/services/slot_memory.py \
  backend/src/agents/nodes/slot_extraction.py \
  backend/src/agents/nodes/clarification_check.py
```

结果：All checks passed。

## 联调注意

- 旧 SQLite 库须重启后端或执行 `init_db` 以应用 `context_state` 列迁移。
- 澄清轮 intentionally 不更新 `context_state`，避免不完整 slots 覆盖 pending。

## 修改文件列表

- `backend/src/services/slot_memory.py`（新建）
- `backend/src/db/models.py`
- `backend/src/db/session.py`
- `backend/src/repositories/session_repository.py`
- `backend/src/integrations/langgraph/state.py`
- `backend/src/integrations/langgraph/runner.py`
- `backend/src/agents/nodes/slot_extraction.py`
- `backend/src/agents/nodes/clarification_check.py`
- `backend/src/agents/nodes/context_preprocess.py`
- `backend/src/integrations/llm/prompts/slots.py`
- `backend/tests/test_slot_memory.py`（新建）
- `backend/tests/test_slot_extraction_multiturn.py`（新建）
- `backend/tests/test_clarification_inherited.py`（新建）
- `docs/agent/response-bad-case.md`（BC-008）
- `.sdd/experience.md`

**本功能已完成，等待 Orchestrator 调度 Tester 验证。**
