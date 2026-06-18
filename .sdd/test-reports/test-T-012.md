# 测试报告：T-012 LangGraph 真实编排

**测试时间**：2026-06-15 13:08 CST  
**Tester Agent ID**：cursor-tester  
**轮次**：第 2 次验收（修复后复验）

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 客户端发送热点、问数、问股或文档问答类问题，展示完整回答且末尾含风险提示 | **PASS** | 8098 真实联调 4 类用例：问数（半导体排行）正文 62 字为超时降级摘要，但 `rich_blocks` 含 5 行 `ranking_table` + 风险提示 ✅；热点（机器人政策催化）1900 字 + 风险提示 ✅（上轮 0 字）；问股（宁德时代）2663 字 + 风险提示 ✅（上轮无标准文案）；澄清（茅台）240 字 + 风险提示 ✅。文档问答本轮未实测（与第 1 轮一致） |
| 2 | 管理端 Trace 时间线与流转图节点一致，状态与耗时可见 | **PASS** | 问数：`…→data_query_agent→tool_call→evidence_merge→quality_check→response_assembly→END`；热点含 `hotspot_agent→rag_retrieval`；问股含 `evidence_gap_check`；澄清走 `clarification_response→END` |
| 3 | 点击 Trace 节点可展开摘要；「查看完整 JSON」可见结构化数据 | **PASS** | 各 trace 首步 `GET …/steps/{step_id}/raw` 均返回 `raw_json` 字段 |
| 4 | 模糊问题展示结构化追问，Trace 可见 clarification 分支 | **PASS** | 「茅台」→ `clarification_check` + `clarification_response`，正文含追问与风险提示 |

## 技术检查

| 检查项 | 结果 | 证据 |
|--------|------|------|
| `ruff check backend/src backend/tests` | **PASS** | All checks passed |
| `mypy backend/src backend/tests` | **PASS** | 179 files, no issues |
| `pytest backend/tests` | **PASS** | 255 passed, 8 skipped |
| `cd frontend && npm run type-check && npm run lint && npm run build` | **PASS** | 三项均通过 |
| 对齐 `docs/agent/langgraph-flow.md` | **PASS** | `graph.py` 使用 `ALL_NODES` 注册；实测节点 ID 与流转图一致 |
| 不得保留 T-007 fallback 为默认路径 | **PASS** | `chat_service.py` 仅 `LangGraphRunner`；`LANGGRAPH_ENV!=local` 返回 503 |
| `GET /api/config/status` LangGraph ready | **PASS** | `orchestration: { name: langgraph, env: local, status: ready }`（8098 重启后实测） |
| 真实 LangGraph 编排执行 | **PASS** | 4 条真实 LLM 全链路，无空 content、无 fallback Trace |
| `frontend/.env` `VITE_API_BASE_URL=/api` | **PASS** | 静态确认 |
| httpx `trust_env=False` | **PASS** | `backend/src/integrations/llm/client.py` 抽检 |
| 意图 Prompt 不得由模型自由测算 | **PASS** | `prompts/intent.py` 含「不得由模型自由测算」；`test_langgraph_intent_prompt_removes_calculator` 在 pytest 全绿中 |
| 前端 Vite 代理 | **PASS** | `vite.config.ts` 含 `/api` 代理，默认 `8099` |

## 第 1 轮 FAIL 项复验

| 上轮问题 | 本轮结果 |
|----------|----------|
| 热点组装超时空答 | ✅ 1900 字正文，`response_assembly` success |
| 问股缺标准风险提示 | ✅ 宁德时代回答含「不构成投资建议」 |
| pytest 3 项失败 | ✅ 255 passed |
| ruff / mypy 未全绿 | ✅ 全绿 |

## 真实联调实测摘要（8098，`LANGGRAPH_ENV=local`，后端已重启加载最新代码）

| 用例 | 耗时 | 正文字数 | 风险提示 | 关键节点 | 备注 |
|------|------|----------|----------|----------|------|
| 茅台 | ~10s | 240 | ✅ | clarification_response | — |
| 今天半导体涨幅排行怎么样 | ~265s | 62（降级摘要） | ✅ | data_query 全链路 | `rich_blocks.ranking_table` 5 行 |
| 机器人板块最近有哪些政策催化 | ~109s | 1900 | ✅ | hotspot 全链路 | 上轮 0 字 |
| 宁德时代基本面怎么样 | ~134s | 2663 | ✅ | 含 evidence_gap_check | 上轮无标准文案 |

原始探测日志：`.sdd/test-reports/_t012_round2_probe.log`

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | 问数链路 `response_assembly` 偶发超时，正文降级为短摘要，依赖 `rich_blocks` 承载表格 | response_assembly | 可记入 T-013 回归观察；非本轮阻塞项 |
| 2 | 8099 端口仍有旧进程（未重启），本轮联调使用 8098 新实例 | 环境 | 用户门禁前统一重启单实例后端 |
| 3 | T-019 知识库扩容 | T-019 | 独立验收 |

## 第 1 轮系统级经验跟进

- 热点空答与问股缺风险提示问题已按经验规则修复并验证通过。
