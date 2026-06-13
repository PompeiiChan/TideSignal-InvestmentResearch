# 测试报告：T-003 会话历史与布局偏好真实 API 闭环

**测试时间**：2026-06-09 01:28:36 CST
**Tester Agent ID**：codex-tester

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户在客户端或管理端点击新建会话，历史列表出现“新对话”，切换到该会话后对话区为空且可输入。 | PASS | 浏览器 1440x900、`VITE_USE_MOCK=false` 下点击“新建会话”，网络请求出现 `POST http://127.0.0.1:5199/api/sessions => 200` 和 `GET /api/sessions/{id} => 200`；页面历史首行显示“新对话”，对话区为空，输入框可见。 |
| 2 | 用户在历史搜索框输入关键词，列表只展示匹配的会话；清空关键词后恢复全部历史。 | PASS | 浏览器输入“半导体”后仅显示匹配会话；后端日志记录 `GET /api/sessions?keyword=%E5%8D%8A%E5%AF%BC%E4%BD%93&page=1&page_size=20 200`。使用 Meta+A/Backspace 清空后，页面恢复 3 条历史，请求列表记录 `GET /api/sessions?keyword=&page=1&page_size=20 200`。 |
| 3 | 用户点击任一历史会话，当前对话区显示该会话的消息内容。 | PASS | 浏览器切换到“今天涨幅靠前的半导体股票有哪些”后，请求 `GET /api/sessions/sess_20260608_001 => 200`，对话区显示用户问题和助手消息“今日半导体板块涨幅靠前的个股如下。”。 |
| 4 | 用户拖拽历史列或 Trace 面板宽度，刷新页面后宽度仍按上次设置展示，且内容不遮挡。 | PASS | 管理端 1440x900 下真实拖拽历史列和 Trace 面板，后端日志记录两次 `PATCH /api/layout/preferences 200`；刷新后请求 `GET /api/layout/preferences 200`，CSS 变量恢复为 `--sidebar-width: 300px`、`--trace-width: 580px`，`scrollWidth=clientWidth=1440`。 |
| 5 | 用户打开历史记录右侧三点菜单并删除某条会话后，该会话从真实会话列表移除；删除当前会话时页面自动切换到下一条会话或展示空状态。 | PASS | 浏览器删除当前“新对话”后，请求列表记录 `DELETE /api/sessions/sess_20260609_012606_002 => 200`，随后 `GET /api/sessions/sess_20260608_001 => 200`；页面自动切回下一条会话。 |

## 技术检查

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | `$PY -m ruff check backend/src backend/tests` 通过 | PASS | `.venv/bin/python -m ruff check backend/src backend/tests` 输出 `All checks passed!`。 |
| 2 | `$PY -m mypy backend/src backend/tests` 通过 | PASS | `.venv/bin/python -m mypy backend/src backend/tests` 输出 `Success: no issues found in 21 source files`。 |
| 3 | `$PY -m pytest backend/tests` 通过 | PASS | `.venv/bin/python -m pytest backend/tests`：5 passed，10 warnings；warnings 来自 pycore Pydantic deprecation，非 T-003 范围。 |
| 4 | 前端 type-check / lint / build 通过 | PASS | `npm run type-check`、`npm run lint`、`npm run build` 均退出 0；build 生成 `dist/`。 |
| 5 | `VITE_USE_MOCK=false` 时目标 API 均命中真实后端 | PASS | 前端以 `VITE_USE_MOCK=false VITE_API_BASE_URL=/api VITE_BACKEND_PROXY_TARGET=http://localhost:8099 npm run dev -- --host 127.0.0.1 --port 5199` 启动；浏览器请求列表覆盖 `GET/POST /api/sessions`、`GET/DELETE /api/sessions/{id}`、`GET/PATCH /api/layout/preferences`，后端 8099 日志均记录 200。 |
| 6 | 请求经 `/api` 代理到 8099，`.env` 保持相对路径 | PASS | `curl --noproxy '*' http://127.0.0.1:5199/api/health` 返回后端 `smart-investment-research-api`；`frontend/.env` 为 `VITE_API_BASE_URL=/api`；`vite.config.ts` 配置 `/api` 代理默认 `http://localhost:8099`。 |
| 7 | 功能页面不再走会话和布局 Mock 分支 | PASS | `frontend/src/services/sessions.ts` 与 `frontend/src/services/layout.ts` 只在 `import.meta.env.VITE_USE_MOCK === 'true'` 时动态 `import('../mocks/mockApi')`；真实联调请求列表未出现 mock-only 行为。 |
| 8 | 固定高度与响应式无明显溢出 | PASS | `.chat-row` `min-height: 56px`，标题省略、菜单按钮固定尺寸；浏览器验证 1440x900 桌面 `scrollWidth=clientWidth=1440`，390x844 客户端和管理端 `scrollWidth=clientWidth=390`。 |

## API 契约与同步检查

- `docs/api-contracts.md` 已包含 `GET /api/layout/preferences` 与 `PATCH /api/layout/preferences` 契约。
- `.sdd/tasks.json` 的 T-003 `technicalChecks` 与 `frontendIntegration.realApiEndpoints` 已包含新增 `GET /api/layout/preferences`。
- 后端路由实现覆盖 `GET/POST /api/sessions`、`GET/DELETE /api/sessions/{session_id}`、`GET/PATCH /api/layout/preferences`。
- T-004 范围的 `POST /api/chat/query`、富响应、真实 Trace API 未纳入本轮 FAIL 判定。

## 安全与稳定性检查

- 未发现真实 API Key、Token、Bearer 值或密码泄露；扫描命中均为配置字段名。
- `httpx.AsyncClient` 仅在测试中使用，均设置 `trust_env=False`。
- `backend/tests/test_sessions_layout.py` 使用临时 SQLite 与 `app.dependency_overrides[get_session]`，未导入运行时 `async_session_maker` 后清表；未发现 `drop_all`。
- pytest 后运行时库 `backend/data/smart_investment.db` 仍包含 `investment_sessions`、`investment_messages`、`layout_preferences`、`users`。
- Zustand selector 未使用 `?? []` / `?? {}` 字面量 fallback；选择器返回 store 中已有引用或函数。

## 执行命令摘要

```bash
.venv/bin/python -m ruff check backend/src backend/tests
.venv/bin/python -m mypy backend/src backend/tests
.venv/bin/python -m pytest backend/tests
cd frontend && npm run type-check
cd frontend && npm run lint
cd frontend && npm run build
cd backend && PYTHONPATH=.. ../.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8099
cd frontend && VITE_USE_MOCK=false VITE_API_BASE_URL=/api VITE_BACKEND_PROXY_TARGET=http://localhost:8099 npm run dev -- --host 127.0.0.1 --port 5199
curl --noproxy '*' http://127.0.0.1:5199/api/health
curl --noproxy '*' http://127.0.0.1:5199/api/layout/preferences
```

## 修改文件

- `.sdd/test-reports/test-T-003.md`
- `.sdd/tasks.json`
- `.sdd/status.json`
