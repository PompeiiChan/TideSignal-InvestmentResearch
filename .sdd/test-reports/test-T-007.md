# 测试报告：T-007 Agent/RAG/质检 fallback 链路闭环

**测试时间**：2026-06-09 12:56:17 CST
**Tester Agent ID**：codex-tester

> 2026-06-11 修订提示：用户验收后追加要求“客户端/管理端可见 UI 不展示 Agent fallback 摘要、当前回答由演示级链路生成、真实 LLM/LangGraph 未接入等内部工程文案”。因此本报告原始第 4 条中的可见 fallback 展示口径已被文末「2026-06-11 追加验收修订」覆盖；后续 Agent 应以后者为准。

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户发送热点、问数或问股类问题后，回答能展示对应的表格、卡片、引用来源和风险提示。 | PASS | 真实浏览器在 `VITE_USE_MOCK=false` 管理端发送“机器人板块最近有哪些政策催化”“今天半导体涨幅排行怎么样”“宁德时代基本面怎么样”；页面分别展示热点摘要、排行表、个股基本面卡、引用来源和“不构成投资建议”风险提示。 |
| 2 | 用户在管理端查看 Trace，能看到意图识别、路由决策、工具调用、RAG 命中和质检合规等步骤。 | PASS | 管理端 Trace 面板展示 7 步：上下文预处理、意图识别、路由决策、工具调用、RAG 命中、质检合规、回答组装。 |
| 3 | 用户打开 Trace 节点详情，能看见命中文档标题、来源类型、相关性说明和质检 PASS / FAIL 结果。 | PASS | 真实浏览器展开 RAG 节点后显示“文档标题 / 来源类型 / 相关性说明”；展开质检节点后显示结果 PASS、引用完整、风险提示已添加。 |
| 4 | 当真实模型 Key、知识库路径或 LangGraph 流转图尚未提供时，页面状态明确显示当前为演示数据或 fallback 链路。 | PASS | Trace 头部显示“演示数据 / fallback 链路”；回答和风险提示说明真实 LLM、真实金融数据 API 与 LangGraph 尚未接入；配置状态 API 返回 mocked 和缺失字段名。 |

## 技术验证

| 检查 | 结果 | 说明 |
|---|---|---|
| `$PY -m ruff check backend/src backend/tests` | PASS | 使用项目 `.venv/bin/python` 执行。 |
| `$PY -m mypy backend/src backend/tests` | PASS | 31 个 source files 无类型错误。 |
| `$PY -m pytest backend/tests` | PASS | 11 passed；仅 pycore 既有 Pydantic v2 deprecation warnings。 |
| `cd frontend && npm run type-check` | PASS | TypeScript 检查通过。 |
| `cd frontend && npm run lint` | PASS | ESLint 通过。 |
| `cd frontend && npm run build` | PASS | Vite production build 通过。 |
| 真实 API / 代理联调 | PASS | 后端 `8099` 与前端 `5199` 启动，`VITE_USE_MOCK=false`；后端日志记录 `POST /api/chat/query` 与 `GET /api/traces/{trace_id}`，`curl http://127.0.0.1:5199/api/config/status` 经 Vite `/api` 代理返回 200。 |
| 测试库隔离 | PASS | pytest 后真实业务库仍有 `investment_sessions`、`investment_messages`、`investment_traces`、`layout_preferences`，记录未被清空。 |

## 外部服务边界

本任务仅验证 fallback 链路。真实 LLM、Embedding、Rerank、本地 Markdown 知识库检索和 LangGraph 编排未进行完整联调；缺失条件仍为用户后续提供对应 Key、Base URL、模型名、LOCAL_KB_PATH、完整 LangGraph 流转图和 Tester 调用权限。

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|----------|--------------|
| 1 | pytest 输出 pycore 的 Pydantic v2 class-based config deprecation warnings。 | pycore 框架依赖 | 当前任务不维护 pycore；后续框架专项升级时统一处理。 |

## 2026-06-11 追加验收修订：富响应 UI 与内部文案清洗

用户验收 T-007 后追加了富响应展示要求，原报告中“页面状态明确显示演示数据 / fallback 链路”“回答和风险提示说明真实 LLM、真实金融数据 API 与 LangGraph 尚未接入”的可见 UI 口径已经废弃。最新结论如下：

| # | 修订项 | 结果 | 说明 |
|---|---|---|---|
| 1 | 客户端不展示 `Agent fallback 回答摘要`、`当前回答由演示级 Agent fallback 链路生成`、`用于验证路由`、`真实 LLM`、`LangGraph` 等内部工程文案。 | PASS | 后端 `message_sanitizer.py` 清洗历史消息和 session preview；前端 `sanitizeResponse.ts` 在 store、ChatView、TracePanel 做防御性过滤。 |
| 2 | 个股基本面回答按 `stock_card -> text -> risk_notice -> citation_list` 组织，且整体仍位于同一个 assistant 气泡内。 | PASS | 个股卡补充毛利率、净利率、经营性现金流量净额；追加 200-300 字基本面点评；风险提示和来源作为回答末尾普通文本。 |
| 3 | 旧 SQLite / 旧 API / 旧 mock 返回脏富响应时，客户端仍不得渲染内部 fallback 摘要。 | PASS | 前端 store 对 session list、session detail、chat query response 清洗；ChatView 渲染前再次清洗。 |

最新验证命令：

- `PYTHONPATH=.. ./.venv/bin/python -m ruff check backend/src backend/tests`
- `PYTHONPATH=.. ./.venv/bin/python -m mypy backend/src backend/tests`
- `PYTHONPATH=.. ./.venv/bin/python -m pytest backend/tests`
- `cd frontend && npm run type-check`
- `cd frontend && npm run lint`
- `cd frontend && npm run build`

当前阶段仍未声明真实 LLM、Embedding、Rerank、本地知识库或 LangGraph 完整联调通过；这些能力仍留到后续真实配置和真实编排任务中处理。
