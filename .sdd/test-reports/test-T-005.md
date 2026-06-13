# 测试报告：T-005 Trace API 与管理端详情闭环

**测试时间**：2026-06-09 12:30:00 CST  
**Tester Agent ID**：codex-tester

## 结果：PASS

## 范围声明

本报告只验证 T-005 fallback Trace 详情闭环。真实 LangGraph 流转图尚未提供，因此不声明真实 LangGraph 编排联调通过。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户在管理端点击某轮问答，右侧 Trace 面板展示该问答的完整步骤时间线、节点状态和耗时。 | PASS | `VITE_USE_MOCK=false` 启动前端后，客户端发送“今天半导体排行怎么样”，切到管理端可见 `Trace 链路`、`Step 1 上下文预处理`、`Step 2 意图路由`、`Step 3 回答组装与质检`，并显示 38ms / 126ms / 256ms。 |
| 2 | 用户点击任一 Trace 节点，节点在当前时间线内展开输入、输出和关键字段摘要。 | PASS | Step 2 默认展开，展示“意图：行情/基本面查询”和“编排模式：fallback Trace，仅验证产品闭环”；节点文案明确“真实 LangGraph 尚未接入”。 |
| 3 | 用户点击“查看完整 JSON”，弹窗展示该节点的结构化 JSON，关闭弹窗后仍停留在原 Trace 面板。 | PASS | 点击“查看完整 JSON”后弹窗展示 `fallback_intent_router`、`response_kind=ranking`、`langgraph_connected=false`；点击可访问名“关闭”后弹窗关闭，仍停留在 `Trace 链路` 面板。 |
| 4 | 用户拖拽 Trace 面板宽度，Trace 节点卡片和中间对话区保持稳定，没有遮挡或溢出。 | PASS | 1440x900 与 390x844 浏览器检查均无页面级横向滚动；移动端表格仅在表格容器内横向滚动，未撑爆页面。Trace 面板在两种宽度均可见。 |

## 技术检查

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | `.venv/bin/python -m ruff check backend/src backend/tests` | PASS | `All checks passed!` |
| 2 | `.venv/bin/python -m mypy backend/src backend/tests` | PASS | `Success: no issues found in 28 source files` |
| 3 | `.venv/bin/python -m pytest backend/tests` | PASS | `8 passed, 10 warnings`；warnings 为 pycore Pydantic v2 deprecation，非 T-005 范围缺陷。 |
| 4 | `cd frontend && npm run type-check` | PASS | `tsc --noEmit` 通过。 |
| 5 | `cd frontend && npm run lint` | PASS | `eslint .` 通过。 |
| 6 | `cd frontend && npm run build` | PASS | `vite build` 通过，`98 modules transformed`。 |
| 7 | 后端 8099 短时启动 | PASS | `PYTHONPATH=.. ../.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8099` 启动成功，日志显示 `Database initialized` 与 `Uvicorn running on http://127.0.0.1:8099`。 |
| 8 | 前端 5199 真实 API 模式 | PASS | `VITE_USE_MOCK=false VITE_BACKEND_PROXY_TARGET=http://localhost:8099 npm run dev -- --host 127.0.0.1 --port 5199 --strictPort` 启动成功。 |
| 9 | Trace API 契约 | PASS | 经 8099 直接 smoke 与 5199 `/api` 代理 smoke，`GET /api/traces/{trace_id}` 返回完整 `steps`，`GET /api/traces/{trace_id}/steps/step_002/raw` 返回 raw JSON。 |
| 10 | Mock 残留检查 | PASS | `frontend/src/services/traces.ts` 仅 `VITE_USE_MOCK=true` 动态导入 `../mocks/mockApi`；真实模式从 `/api/traces/...` 读取后端数据。 |
| 11 | fallback 外部服务口径 | PASS | Trace raw JSON 与节点文案均标记 `langgraph_connected=false` / fallback Trace，不声明真实 LangGraph 编排。 |
| 12 | 测试数据库隔离 | PASS | `backend/tests/test_sessions_layout.py` 使用 tmp SQLite 和 `app.dependency_overrides[get_session]`，未清理运行时业务库。 |

## 关键代码证据

- `backend/src/db/models.py`：新增 `TraceRecord` 持久化完整 fallback Trace。
- `backend/src/services/trace_service.py`：生成 3 步 fallback timeline，读取完整 Trace 与单节点 raw JSON。
- `backend/src/api/routes/traces.py`：注册 `GET /api/traces/{trace_id}` 与 `GET /api/traces/{trace_id}/steps/{step_id}/raw`。
- `backend/src/services/chat_service.py`：`POST /api/chat/query` 持久化 assistant message 后同步写入完整 Trace。
- `frontend/src/services/traces.ts`：真实模式调用后端 Trace API，Mock 模式才动态加载 Mock。
- `frontend/src/stores/useInvestmentStore.ts`：真实模式发送 Query 后拉取完整 Trace；历史切换遇到 summary 时补拉 detail。
- `frontend/src/components/TracePanel.tsx`：展示 steps、内联展开 detail sections，并打开 raw JSON 弹窗。

## 超出范围发现

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | 当前 Trace 是 fallback timeline，不是真实 LangGraph 运行图。 | 后续 LangGraph 编排 | 用户提供完整流转图和运行配置后，在后续任务中替换 fallback Trace 生成逻辑并补真实编排测试。 |
