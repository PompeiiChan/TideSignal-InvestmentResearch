# 测试报告：T-006 数据源状态与系统设置真实 API 闭环

**测试时间**：2026-06-09 12:40:00 CST  
**Tester Agent ID**：codex-tester

## 结果：PASS

## 范围声明

本报告只验证数据源状态与系统设置状态的真实 API fallback 闭环。真实 LLM、Embedding、Rerank、本地知识库检索和 LangGraph 编排尚未提供完整配置，因此不声明这些外部服务真实联调通过。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户打开数据说明页，能看到行情、财务、公告、研报、知识库等本地数据源的状态、路径说明和样本数量。 | PASS | 真实浏览器访问 `/client/data`，页面显示行情数据、财务数据、研报数据、公告数据、投研知识库，并展示 `data/mock/...` 路径、`mocked` 状态和样本数量。 |
| 2 | 用户打开系统设置页，能看到 LLM、Embedding、Rerank 的字段名、当前状态和缺失项，但看不到任何真实密钥内容。 | PASS | 真实浏览器访问 `/admin/settings`，页面显示 `LLM_API_KEY`、`EMBEDDING_API_KEY`、`RERANK_API_KEY` 等字段名，状态为 `mocked`，缺失字段可见；页面文本未出现 `sk-`、`Bearer` 或长 token 样式内容。 |
| 3 | 用户在管理端能看到 Prompt 默认配置和合规黑名单表达，客户端仍不展示系统设置入口。 | PASS | 管理端系统设置页显示 Prompt 模块、总控 Agent、质检模块、黑名单表达和 `风险提示必需：true`；客户端 `/client/data` 页面导航只显示“对话 / 数据说明”，不显示“系统设置”。 |
| 4 | 当外部服务 Key 尚未提供时，页面清楚显示 mocked 或 missing 状态，不把能力描述成真实已接入。 | PASS | 两个接口返回外部模型状态 `mocked`，RAG 状态 `mocked`；报告不声明真实外部服务联调通过。 |

## 技术检查

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | `.venv/bin/python -m ruff check backend/src backend/tests` | PASS | `All checks passed!` |
| 2 | `.venv/bin/python -m mypy backend/src backend/tests` | PASS | `Success: no issues found in 31 source files` |
| 3 | `.venv/bin/python -m pytest backend/tests` | PASS | `10 passed, 10 warnings`；warnings 为 pycore Pydantic v2 deprecation，非 T-006 范围缺陷。 |
| 4 | `cd frontend && npm run type-check` | PASS | `tsc --noEmit` 通过。 |
| 5 | `cd frontend && npm run lint` | PASS | `eslint .` 通过。 |
| 6 | `cd frontend && npm run build` | PASS | `vite build` 通过，`100 modules transformed`。 |
| 7 | `GET /api/data-sources/status` 与 `GET /api/config/status` 真实后端 | PASS | 8099 直接 smoke 返回 `code=200`；数据源 5 类，RAG `mocked`，模型状态均 `mocked`。 |
| 8 | Vite `/api` 代理到真实后端 | PASS | 5199 `/api/data-sources/status` 返回 `200 5 mocked`；5199 `/api/config/status` 返回 `200 ['mocked', 'mocked', 'mocked'] True`。 |
| 9 | 密钥泄露扫描 | PASS | 扫描命中仅为测试断言、字段名、前端 Authorization 代码和既有 SVG/CSS 文本；未发现真实 Key、Token、Secret 或可还原片段。 |
| 10 | 桌面与移动布局 | PASS | 1440x900 与 390x844 分别检查 `/client/data` 和 `/admin/settings`，`bodyScrollWidth == clientWidth`，无页面级横向溢出。 |

## 关键代码证据

- `backend/src/models/config_status.py`：定义数据源状态、模型状态、Prompt、合规规则 DTO。
- `backend/src/services/config_status_service.py`：返回只读状态，不读取进程环境变量，不返回真实密钥值。
- `backend/src/api/routes/config_status.py`：注册 `GET /api/data-sources/status` 与 `GET /api/config/status`。
- `frontend/src/services/dataSources.ts`：真实模式调用 `/api/data-sources/status`，Mock 模式才动态加载 Mock。
- `frontend/src/services/config.ts`：真实模式调用 `/api/config/status`，Mock 模式才动态加载 Mock。
- `frontend/src/stores/useInvestmentStore.ts`：进入数据说明页或管理端系统设置页时加载真实状态。
- `frontend/src/components/DataPage.tsx` / `SettingsPage.tsx`：展示状态、字段名、缺失字段、Prompt 与合规规则。

## 超出范围发现

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | 当前数据源目录未放真实本地 Markdown / 金融数据样本，因此 API 使用内置 fallback 样本数并标记 `mocked`。 | 后续 Agent/RAG 或数据接入 | 用户提供 `LOCAL_KB_PATH`、`MOCK_DATA_PATH` 和真实样本后，再把状态升级为真实 ready 并补联调验证。 |
