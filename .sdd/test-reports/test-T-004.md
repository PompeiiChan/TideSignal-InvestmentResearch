# 测试报告：T-004 Chat Query 与富响应 fallback 闭环

**测试时间**：2026-06-09 07:42:27 CST  
**Tester Agent ID**：codex-tester  

## 结果：PASS

## 范围声明

本报告只验证 T-004 fallback 闭环。未声明真实 LLM、真实金融数据 API、LangGraph 完整流转、T-005 完整 Trace 详情 API、T-006 数据源 / 设置 API 联调通过。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户在客户端输入投研问题并发送，页面显示用户消息和助手回答，回答包含结构化表格或卡片、引用来源和风险提示。 | PASS | 1440x900 浏览器在 `/client` 发送 `18元买入未来预期回报率怎么算` 后，页面显示用户消息、助手回答、`fallback 回答摘要`、`引用来源`、`风险提示` 和“不构成投资建议”。接口响应包含 `assistant_message.rich_blocks` 的 `text`、`calculator`、`citation_list`、`risk_notice`。 |
| 2 | 用户发送收益测算类问题后，页面展示可交互测算组件；用户修改买入价、情景价或持仓数量，收益率和盈亏实时变化。 | PASS | 浏览器中计算器初始显示买入价 15、情景价 20、持仓 1000；修改为 10、25、200 后结果实时变为收益率 `149.90%`、预估盈亏 `2,997.90 元`、测算成本 `2,000.00 元`。 |
| 3 | 用户发送新会话的第一条问题后，历史标题从“新对话”替换为该问题内容。 | PASS | 浏览器点击“新建会话”后历史项显示“新对话”；发送首问后同一历史项替换为 `18元买入未来预期回报率怎么算`。接口返回 `session.title_source=first_query`、`is_draft=false`。 |
| 4 | 用户切换到管理端查看同一会话，能看到同一轮 Query、Response 和 Trace 摘要。 | PASS | 浏览器切换到 `/admin` 后，同一会话仍显示 Query 和 Response，右侧 Trace 面板显示 `基础 Trace 摘要`、`420ms`、工具调用 `0`、质检 `PASS`、`fallback-master / local-fallback`。 |

## 技术检查

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | `.venv/bin/python -m ruff check backend/src backend/tests` | PASS | `All checks passed!` |
| 2 | `.venv/bin/python -m mypy backend/src backend/tests` | PASS | `Success: no issues found in 24 source files` |
| 3 | `.venv/bin/python -m pytest backend/tests` | PASS | `7 passed, 10 warnings`；warnings 为 pycore Pydantic v2 deprecation，非 T-004 范围缺陷。 |
| 4 | `cd frontend && npm run type-check` | PASS | `tsc --noEmit` 通过。 |
| 5 | `cd frontend && npm run lint` | PASS | `eslint .` 通过。 |
| 6 | `cd frontend && npm run build` | PASS | `vite build` 通过，`97 modules transformed`。 |
| 7 | 后端从 `backend/` 使用 `PYTHONPATH=..` 和 8099 短时启动 | PASS | `PYTHONPATH=.. ../.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8099` 启动成功，日志显示 `Database initialized` 和 `Uvicorn running on http://127.0.0.1:8099`。 |
| 8 | Vite 5199 且 `VITE_USE_MOCK=false` 真实代理 | PASS | `VITE_USE_MOCK=false VITE_BACKEND_PROXY_TARGET=http://localhost:8099 npm run dev -- --host 127.0.0.1 --port 5199` 启动成功；Playwright 网络记录出现 `POST http://127.0.0.1:5199/api/chat/query => 200`，后端 8099 日志同步出现 `POST /api/chat/query HTTP/1.1 200 OK`。 |
| 9 | `POST /api/chat/query` 契约字段与持久化回读 | PASS | 经 5199 `/api` 代理创建会话并 POST chat query，响应 `data` 包含 `session`、`user_message`、`assistant_message`、`trace`；随后 `GET /api/sessions/{session_id}` 回读到同一轮 user / assistant 消息、更新后的 title、`last_message_preview` 和 `last_trace_id`。 |
| 10 | `VITE_USE_MOCK=false` 不走 `frontend/src/mocks` chat query 分支 | PASS | `frontend/src/services/chat.ts` 仅 `VITE_USE_MOCK === 'true'` 时动态导入 `../mocks/mockApi`；Playwright 静态/网络记录未出现 `mockApi` / `mocks` 请求，业务请求均为 `/api/...`。页面无 `[Mock]` 标签。 |
| 11 | fallback 外部服务口径 | PASS | 响应风险提示明确“本地模拟数据和 fallback 规则”“真实 LLM、真实金融数据 API 与 LangGraph 流转尚未接入”；本报告不声明外部服务完整联调通过。 |
| 12 | httpx/openai 环境继承 | PASS | `backend/src` 未发现 `httpx` / `openai` 调用；测试中 `httpx.AsyncClient` 均设置 `trust_env=False`。 |
| 13 | 桌面与移动无明显溢出 | PASS | Playwright 桌面 1440x900：`bodyScrollWidth=1440`、`docScrollWidth=1440`；移动 390x844：`bodyScrollWidth=390`、`docScrollWidth=390`。富响应、计算器和 Trace 摘要可见。 |
| 14 | 测试数据库隔离 | PASS | `backend/tests/test_sessions_layout.py` 使用 tmp SQLite 和 `app.dependency_overrides[get_session]`；pytest 后运行时库仍有 `investment_sessions`、`investment_messages`、`layout_preferences`、`users` 表。 |

## 关键代码证据

- `backend/src/models/chat.py`：`ChatQueryResponse` 定义 `session`、`user_message`、`assistant_message`、`trace`。
- `backend/src/services/chat_service.py`：`ChatService.query()` 持久化 user / assistant 两条消息，首问更新标题，返回 fallback rich blocks 和基础 Trace summary。
- `backend/src/api/routes/chat.py`：注册 `POST /api/chat/query`，空 query 返回 422，会话不存在返回 404。
- `frontend/src/services/chat.ts`：真实模式走 `api.post('/chat/query', request)`。
- `frontend/src/stores/useInvestmentStore.ts`：真实模式保存 `POST /api/chat/query` 返回的 Trace summary，不提前调用 T-005 完整 Trace API。
- `frontend/src/components/RichBlockRenderer.tsx`：渲染 calculator / citation / risk blocks，并在本地实时计算收益率和盈亏。
- `frontend/src/components/TracePanel.tsx`：当 trace 无 steps 时展示 T-004 基础 Trace 摘要。

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | 真实模式刷新后如果只依赖 `last_trace_id`，当前前端会生成本地 fallback Trace summary 占位，不会调用完整 Trace 详情；这符合 T-004 避免提前命中 T-005 的边界。 | T-005 Trace API | T-005 实现 `GET /api/traces/{trace_id}` 后再补完整 Trace 回读。 |
