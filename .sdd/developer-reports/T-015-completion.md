# T-015 五轮短期记忆窗口 — 开发完成报告

> **任务 ID**：T-015  
> **完成日期**：2026-06-19  
> **状态**：待 Tester 验证（`testing`）

---

## 实现摘要

1. 新建 `backend/src/services/short_term_memory.py`，统一五轮 QA 窗口截断与 `history_summary` 生成；`trim_chat_history` 在截断前先 `exclude_trailing_user`，避免当前轮 user 占用窗口并产生孤儿 assistant 片段。
2. `AppSettings.short_term_qa_rounds`（默认 5）可通过 `SHORT_TERM_QA_ROUNDS` 环境变量覆盖；`LangGraphRunner._build_chat_history` 与 `context_preprocess` 共用该模块。
3. `context_preprocess` Trace 的 `input` 含 `history_truncated` / `history_window_rounds` / `history_total_messages`；`context_pack` 与 `output.history_summary` 对齐截断后历史。
4. `integrations/llm/prompts/intent.py` 增加「多轮续问 / history_summary」规则及宁德时代→一季报续问 few-shot。

---

## 变更文件

| 文件 | 变更 |
|------|------|
| `backend/src/services/short_term_memory.py` | 新建 |
| `backend/src/settings.py` | `short_term_qa_rounds` + env 映射 |
| `backend/config/app.toml` | 默认 `short_term_qa_rounds = 5` |
| `backend/.env.example` | `SHORT_TERM_QA_ROUNDS` 注释 |
| `backend/src/integrations/langgraph/runner.py` | `_build_chat_history` 接入 `trim_chat_history` |
| `backend/src/agents/nodes/context_preprocess.py` | 删除本地常量，共用 short_term_memory + trace meta |
| `backend/src/integrations/llm/prompts/intent.py` | 续问规则与 few-shot |
| `backend/tests/test_short_term_memory.py` | 新建（4 用例） |
| `backend/tests/test_langgraph_trace.py` | 续问 prompt + mock LLM 意图单测 |

---

## 测试结果

```text
PYTHONPATH=. .venv/bin/python -m pytest backend/tests/test_short_term_memory.py backend/tests/test_langgraph_trace.py -q
→ 8 passed

.venv/bin/python -m ruff check backend/src/services/short_term_memory.py \
  backend/src/agents/nodes/context_preprocess.py \
  backend/src/integrations/langgraph/runner.py
→ All checks passed
```

---

## 验收映射

| acceptanceCriteria | 实现 |
|--------------------|------|
| 第 6 轮起仅保留 5 轮 QA | `trim_chat_history` 单测 + runner 调用 |
| Trace `context_preprocess` 可见 `history_count`、截断后 `history_summary` | `input_data` / `context_pack` / `output` 字段 |
| 续问意图识别 | intent prompt few-shot + `test_intent_follow_up_with_mock_llm` |

---

## 未实现（按方案排除）

- T-014 Query 改写
- T-016 槽位跨轮继承
- T-017 下游节点历史注入
