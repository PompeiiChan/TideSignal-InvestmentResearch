# T-017 多轮上下文注入下游节点（F20）— 技术方案

> **任务 ID**：T-017  
> **依据文档**：`docs/agent/langgraph-flow.md` §7.3、`.sdd/tasks.json`  
> **前置**：T-015（窗口 + `history_summary`）✅、T-016（`pending_slots` / `active_slots`）✅  
> **产出日期**：2026-06-19  
> **状态**：待 Developer 执行

---

## 1. 背景与目标

### 1.1 现状

| 节点 | 多轮上下文 |
|------|------------|
| `intent_recognition` | ✅ `history_summary` |
| `slot_extraction` | ✅ `pending_slots` + `history_summary` → `active_slots` |
| `stock_analysis_agent` | ❌ 仅 `normalized_query` + `slots` |
| `evidence_merge` | ❌ `evidence_pack` 无 `conversation_context` |
| `response_assembly` | ❌ user prompt 仅 `用户问题：{normalized_query}` |
| `rag_retrieval` | 部分用 `slots.stock_name` 过滤，Trace 无 carryover 字段 |

T-016 后续问不再澄清，但子 Agent / 组装层仍可能把「一季报呢」当孤立短句，回答标的或时间口径断裂。

### 1.2 目标

1. 构建统一 **`conversation_context`**（结构化 carryover），供下游消费。
2. **`stock_analysis_agent`**、**`response_assembly`** 注入 `history_summary` + `active_slots`。
3. **`evidence_pack.conversation_context`** 写入 Trace，组装 Prompt 可读。
4. **首轮无历史**时行为与现网一致（空 context 不注入）。
5. RAG 仍用 `normalized_query`；**`slots.stock_name`（含继承）** 继续参与 `entity_name` / narrative 过滤。

### 1.3 非目标

- Query 改写 / `retrieval_query`（**T-014**）
- 新 DB 字段（复用 state 流转）
- 全量子 Agent 大改（`data_query_agent` / `hotspot_agent` 仅在有 `active_slots` 时轻量传入，非 AC 主路径）

---

## 2. 新建 `backend/src/services/conversation_context.py`

```python
def build_conversation_context(
    *,
    history_summary: str,
    active_slots: dict[str, Any],
    inherited_slot_keys: list[str] | None = None,
    normalized_query: str = "",
) -> dict[str, Any]:
    """Return structured carryover; empty dict when no multi-turn signal."""

def format_conversation_context_for_prompt(ctx: dict[str, Any]) -> str:
    """Human-readable block for LLM user prompts."""
```

**`conversation_context` 结构**：

```json
{
  "has_context": true,
  "history_summary": "user: 宁德时代…\nassistant: …",
  "active_slots": { "stock_name": "宁德时代", "stock_code": "300750.SZ", "time_range": "2026Q1" },
  "inherited_slot_keys": ["stock_name", "stock_code"],
  "carryover_hint": "续问：用户在上轮已讨论宁德时代基本面，本轮关注一季报。"
}
```

**`has_context` 判定**：

- `history_summary` 非空 **且**（`active_slots` 含 `stock_name`/`industry`/`topic` 等关键键 **或** `inherited_slot_keys` 非空）
- 否则返回 `{"has_context": false}`（首轮单轮）

**窗口约束**：`history_summary` 已由 T-015 截断至 5 轮 QA；本模块不再扩窗。

---

## 3. 节点改动

### 3.1 `context_preprocess.py`（轻量）

- 在 output / `context_pack` 增加 `conversation_context`（调用 `build_conversation_context`，此时 `active_slots` 可能尚未合并，可仅写 `history_summary` 占位；**或在 slot_extraction 之后由下游从 state 构建**）

> **决策**：在 **`slot_extraction` 输出后**由 state 已有 `active_slots` + `history_summary` 构建；`context_preprocess` 不重复。新增辅助函数 `enrich_state_conversation_context(state) -> dict` 供各节点调用。

### 3.2 `slot_extraction.py`

- output 后 state 已有 `active_slots`；trace 可选增加 `conversation_context` 预览（`has_context` + `active_slots` keys）

### 3.3 `stock_analysis_agent.py`

```python
conversation_context = build_conversation_context(
    history_summary=state.get("history_summary", ""),
    active_slots=state.get("active_slots") or state.get("slots") or {},
    inherited_slot_keys=state.get("inherited_slot_keys") or [],
    normalized_query=normalized_query,
)
input_data = {
    "normalized_query": normalized_query,
    "slots": slots,
    "active_slots": state.get("active_slots") or slots,
    "history_summary": ...,
    "conversation_context": conversation_context,
    "intent_id": intent_id,
}
```

### 3.4 `integrations/llm/prompts/agents/stock_analysis.py`

增加 **「多轮续问」** 规则：

- 当 `conversation_context.has_context=true`，规划须延续 `active_slots.stock_name` 与时间口径（如 `time_range`）
- 短续问（「一季报呢」）须在 `agent_result` 明确分析对象与报告期
- few-shot 示例

### 3.5 `evidence_merge.py`

```python
conversation_context = build_conversation_context(...)
evidence_pack = {
    ...
    "conversation_context": conversation_context,
    "active_slots": slots,
}
```

trace `input_data` 增加 `has_conversation_context`。

### 3.6 `response_assembly.py`

**input_data**（Trace 可见）：

```python
{
    "query": normalized_query,
    "history_summary": ...,
    "active_slots": ...,
    "conversation_context": ...,
    "response_kind": ...,
}
```

**user_prompt** 追加（当 `has_context`）：

```text
【多轮对话上下文】
{format_conversation_context_for_prompt(...)}
须延续上述标的与时间口径作答，不得要求用户重复提供公司名称。
```

### 3.7 `integrations/llm/prompts/assembly.py`

`ASSEMBLY_STOCK_PROMPT_BASE` 增加多轮约束（与 stock agent 一致，1 段）。

### 3.8 `rag_retrieval.py`

- trace `input_data` 增加 `active_slots`、`stock_name`（来自 slots）
- 默认 retrieve 路径：当 `normalized_query` 短且 `slots.stock_name` 有值，确保 `entity_name=stock_name` 传入 `retrieve` / `filter_hits_by_entity`（核查 `rag.retrieve` 调用链，缺则补）

---

## 4. `state.py`

```python
conversation_context: dict[str, Any]
```

可选：在 `slot_extraction` 节点 return 时写入 state（通过 output 字段）。

---

## 5. 测试计划

### 5.1 `test_conversation_context.py`

| 用例 | 断言 |
|------|------|
| 首轮空 | `has_context=false` |
| 续问 | `has_context=true`，carryover_hint 含公司名 |
| format_for_prompt | 非空字符串 |

### 5.2 `test_response_assembly_multiturn.py`

mock LLM client，捕获 user message：

| 用例 | 断言 |
|------|------|
| 有 conversation_context | user prompt 含「多轮对话上下文」与宁德时代 |
| 无历史 | 不含多轮块 |

### 5.3 `test_stock_analysis_agent_multiturn.py`

mock `call_intent_json`：payload 含 `conversation_context` / `active_slots`

### 5.4 `test_evidence_merge_context.py`

`evidence_pack.conversation_context.has_context == true`

### 5.5 回归

```bash
PYTHONPATH=. .venv/bin/python -m pytest \
  backend/tests/test_conversation_context.py \
  backend/tests/test_response_assembly_multiturn.py \
  backend/tests/test_stock_analysis_agent_multiturn.py \
  backend/tests/test_evidence_merge_context.py \
  backend/tests/test_slot_extraction_multiturn.py -q
```

---

## 6. 验收映射

| AC | 验证 |
|----|------|
| 续问回答延续标的/时间 | assembly prompt + 用户门禁 |
| Trace 含 history_summary / active_slots | response_assembly、slot_extraction input |
| 首轮无回归 | conversation_context 空时不注入 |

---

## 7. 收尾

- `.sdd/developer-reports/T-017-completion.md`
- `.sdd/experience.md`
- `.sdd/tasks.json` → `testing`
- Commit：`feat(T-017): 多轮上下文注入下游节点`

---

## 8. Developer Checklist

1. [ ] `conversation_context.py`
2. [ ] `stock_analysis_agent` + prompt
3. [ ] `evidence_merge` conversation_context
4. [ ] `response_assembly` + assembly prompt
5. [ ] `rag_retrieval` trace + entity 过滤核查
6. [ ] 单测
7. [ ] 文档/commit
