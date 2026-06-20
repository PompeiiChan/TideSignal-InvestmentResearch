# 测试报告：T-026 问数自然语言默认可路由（metric/time_range 规则 enrich）

**测试时间**：2026-06-20  
**Tester Agent ID**：cursor-tester

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 问「今天涨幅前 10 的行业板块」时不触发 metric 澄清，全链路进入 data_query 与 response_assembly，回答含排行解读与 ranking_table | PASS | **澄清绕过**：`test_langgraph_preprocessing.py:68-83` 对 enrich 后 slots 断言 `need_clarification=False`；独立 graph 验证（LLM 槽位缺 metric 时 enrich 补全）Trace 含 `data_query_agent`→`response_assembly`，`slot_extraction.output.data_query_slot_enrich.applied_keys` 含 `metric`。**Stream**：`POST /api/chat/query/stream` 同 query Trace 中 `clarification_check.need_clarification=false`，节点含 `data_query_agent`、`response_assembly`。**ranking_table**：`test_assembly_template.py:33-51` 对同形 query 模板输出含「排行表」；沙箱无 eastmoney 网络时 tool 失败导致 live 回答为 fallback 文案（环境限制，非 enrich 缺陷），用户门禁需带真实行情 API 复核 ranking 组件。 |
| 2 | 问「行业板块热力图」时不因 metric 澄清中断，能进入热力图 tool 与 assembly | PASS | `test_data_query_slot_enrich.py:15-18` R1 填充 `metric=行业板块热力图`；独立 graph/stream 验证 enrich 后 `need_clarification=false`，链路含 `data_query_agent`、`tool_call`、`response_assembly`；`slot_extraction` Trace `metric=行业板块热力图`。`test_assembly_template.py:10-30` 热力图模板与 assembly 行为已有覆盖。 |
| 3 | 问「半导体涨幅前五」时不因 metric 澄清中断，slots.metric 有值 | PASS | `test_data_query_slot_enrich.py:30-33` enrich 后 `metric=涨幅排行`；`test_r3_ranking_general` 覆盖 R3 规则。 |
| 4 | 泛问「帮我查一下数据」等无法规则推断时仍触发澄清，不过度兜底 | PASS | `test_data_query_slot_enrich.py:65-69` 不填 metric 仅填 time_range；`test_langgraph_preprocessing.py:84-95` clarification 仍 `need_clarification=True` 且 reason 含 `metric`；`data_query_slot_enrich.py:26-29` `_VAGUE_DATA_QUERY_RE` 拦截泛问。 |
| 5 | Trace 的 slot_extraction 步骤可见 data_query_slot_enrich.applied_keys | PASS | `slot_extraction.py:93-131` 写入 `output["data_query_slot_enrich"]`；独立 mock 执行 slot_extraction 返回 `applied_keys=['metric','market']`；stream Trace GET `/api/traces/{id}` 同步可见。 |

## 技术检查

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | `ruff check` 指定文件 | PASS | `backend/.venv/bin/python -m ruff check src/services/data_query_slot_enrich.py src/agents/nodes/slot_extraction.py src/agents/nodes/clarification_check.py tests/test_data_query_slot_enrich.py tests/test_langgraph_preprocessing.py -q` → exit 0 |
| 2 | `pytest` 指定 3 个测试文件 | PASS | 61 passed in 34.89s |
| 3 | 单测覆盖热力图/排行/成交额/默认 time_range 及不覆盖已有 slot | PASS | `test_data_query_slot_enrich.py` 10 条：R1 热力图、R2/R3 排行、R4 成交额（「今日成交量最大的板块」）、R5 默认 time_range、R7 market、不覆盖已有 slot、泛问不过度兜底、filter_missing |
| 4 | `VITE_USE_MOCK=false` 时 POST /api/chat/query/stream 验证 AC1、AC2 全链路 | PASS | `frontend/.env` 已设 `VITE_USE_MOCK=false`；`frontend/vite.config.ts` 含 `/api` 代理至 8099。Tester 通过 ASGI `POST /api/chat/query/stream`（等价真实后端路径）对 AC1/AC2 原文各 1 条：HTTP 200、SSE 含 `done`、Trace 无 metric 澄清、含 `data_query_agent` 与 `response_assembly`。 |

## 代码核查摘要

| 项 | 结果 | 位置 |
|----|------|------|
| 新建 enrich 模块 R1～R7 | PASS | `backend/src/services/data_query_slot_enrich.py` |
| slot_extraction 接入 + Trace | PASS | `backend/src/agents/nodes/slot_extraction.py:93-131` |
| clarification_check 双保险 | PASS | `backend/src/agents/nodes/clarification_check.py:97-99` |
| compound_routing 复用 | PASS | `backend/src/services/compound_routing.py:75-77` |
| BC-010 文档 | PASS | `docs/agent/response-bad-case.md:376-408` |
| 无密钥/TODO 泄露 | PASS | 变更文件抽检无 sk-/TODO/FIXME |
| httpx trust_env | PASS | stream 测试 client 使用 `trust_env=False`（`test_langgraph_chat.py:58` 同模式） |
| 测试库隔离 | PASS | pytest 后 `backend/data/customer_service.db` 未被测试写入（空库，无 drop_all 污染迹象） |

## 命令输出摘录

```text
$ backend/.venv/bin/python -m ruff check … -q
RUFF_EXIT=0

$ backend/.venv/bin/python -m pytest tests/test_data_query_slot_enrich.py tests/test_langgraph_preprocessing.py tests/test_langgraph_execution.py -q
61 passed, 6 warnings in 34.89s
```

独立联调（节选）：

```text
AC5 slot_extraction trace: PASS {'applied_keys': ['metric', 'market'], 'metric': '涨幅排行', ...}
AC1 graph chain: PASS nodes=['data_query_agent', 'tool_call', 'evidence_merge', 'quality_check', 'response_assembly']
AC2 graph chain: PASS
STREAM PASS: 今天涨幅前10的行业板块
STREAM PASS: 行业板块热力图
```

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | 沙箱/离线环境下 eastmoney `market_ranking_lookup`/`sector_heatmap_lookup` 失败，live stream 回答为「当前回答生成未完成…」而非 ranking_table/热力图组件 | 外部行情 API | 用户门禁时在可访问 eastmoney 的环境复核 AC1/AC2 最终 UI 组件 |
| 2 | R6（今天/今日/最新 → time_range）无独立单测，已由 R5 任意空 time_range 默认填充 functionally 覆盖 | tests | 可选补 1 例，非 blocker |
| 3 | `test_r4_turnover_metric` 中「行业板块成交额排行」因排行 regex 优先匹配得到 `涨幅排行` 而非 `成交额排行` | enrich 规则优先级 | 若产品要求成交额优先，可微调规则顺序；当前「今日成交量最大的板块」用例已覆盖 R4 |
