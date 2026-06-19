# 测试报告：T-015 五轮短期记忆窗口（F20）

**测试时间**：2026-06-19  
**Tester Agent ID**：cursor-tester

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 同一会话第 6 轮起，Agent 上下文仅保留最近 5 轮 QA，更早消息不进入 `chat_history` / `history_summary` | **PASS** | `trim_chat_history` 在 `exclude_trailing_user=True` 时先剥离尾部 user，再按 `max_qa_rounds*2` 截取；`test_trim_keeps_five_rounds_on_sixth_turn`、`test_round_seven_drops_oldest_pair` 断言 u1/a1 被丢弃且首条为 u2；`runner._build_chat_history` 与 `context_preprocess` 均调用同一模块 |
| 2 | 管理端 Trace 的 `context_preprocess` 步骤可看到 `history_count` 与截断后的 `history_summary` | **PASS** | `context_preprocess` 的 `input_data` 含 `history_count`、`history_truncated`、`history_window_rounds`、`history_total_messages`；`output` 含 `history_summary`（基于截断后 `chat_history` 的 `summarize_chat_history`）；`context_pack` 同步 `history_count` 等 meta；经 `run_node_with_trace` 写入 trace step |
| 3 | 续问场景在意图识别阶段结合 `history_summary` 判定为 stock_analysis（测试用例） | **PASS** | `INTENT_SYSTEM_PROMPT_BASE` 含「多轮续问 / history_summary」与「一季报呢」few-shot；`test_intent_follow_up_with_mock_llm` mock `call_intent_json` 验证 payload 含 `history_summary` 且返回 `stock_analysis` |

## technicalChecks

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | 短期记忆窗口单一配置源，runner 与 context_preprocess 共用 | **PASS** | `AppSettings.short_term_qa_rounds`（默认 5，`SHORT_TERM_QA_ROUNDS` env）；`runner.py:80-84`、`context_preprocess.py:72-76` 均调用 `trim_chat_history(..., max_qa_rounds=settings.short_term_qa_rounds)`；逻辑集中在 `short_term_memory.py` |
| 2 | `docs/PRD.md`、`docs/Plan.md` F20 与实现参数一致（5 轮 QA） | **PASS** | PRD §5.3「仅保留最近 **5 轮 QA**」；Plan F20「短期对话记忆（5 轮 QA）」；`app.toml` / `settings.py` 默认 `short_term_qa_rounds = 5` |
| 3 | pytest 含短期记忆与 history_summary 单测 | **PASS** | 见下方命令输出（8 passed） |

## 代码审查要点

| 要点 | 结果 | 位置 |
|------|------|------|
| exclude trailing user | **PASS** | `short_term_memory.py:26-29` 截断前剥离尾部 `role=user` |
| 单一配置源 | **PASS** | 无 `_MAX_HISTORY_MESSAGES` 残留；`context_preprocess` 删除本地 `_summarize_history` |
| trace meta 对齐 | **PASS** | `input_data` + `context_pack` + `output.history_summary` 字段一致 |
| 密钥泄露 | **PASS** | 变更文件无真实 API Key / Token |
| TODO/FIXME | **PASS** | 变更文件无遗留标记 |

## 命令执行摘要

### pytest（项目根，推荐）

```bash
cd Projects_Repo/smart-investment-research
PYTHONPATH=. .venv/bin/python -m pytest \
  backend/tests/test_short_term_memory.py \
  backend/tests/test_langgraph_trace.py -v
```

```text
8 passed in 0.53s
```

### pytest（backend 目录，路径须为 tests/ 非 backend/tests/）

```bash
cd backend && PYTHONPATH=.. ../.venv/bin/python -m pytest \
  tests/test_short_term_memory.py tests/test_langgraph_trace.py -v
```

```text
8 passed in 0.35s
```

> **注**：任务说明中 `cd backend && ... backend/tests/...` 因 cwd 已为 `backend/` 会导致「file not found」；改用 `tests/` 或从项目根执行即可。

### ruff（项目根）

```bash
.venv/bin/python -m ruff check \
  backend/src/services/short_term_memory.py \
  backend/src/agents/nodes/context_preprocess.py \
  backend/src/integrations/langgraph/runner.py \
  backend/src/integrations/llm/prompts/intent.py
```

```text
All checks passed!
```

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|-------------|
| 1 | `context_preprocess` 节点尚无独立单测断言 trace `input/output` 的 `history_count`/`history_summary` 字段（依赖代码路径 + `run_node_with_trace` 契约） | 测试覆盖 | 可选补充 `test_langgraph_preprocessing` 用例；非 T-015 blocker |
| 2 | T-017 下游节点（slot_extraction、response_assembly）尚未注入 `history_summary` | T-017 | 按 backlog 推进 |

## 结论

**T-015 技术验收 PASS。** 五轮 QA 窗口截断、Trace meta、续问意图 prompt 与 mock 单测均符合 acceptanceCriteria 与 technicalChecks。等待用户门禁确认（见 `acceptance-roadmap-T-015.md`）。
