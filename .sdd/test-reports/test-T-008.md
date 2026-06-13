# 测试报告：T-008 全链路 E2E 回归与启动说明

**测试时间**：2026-06-11 14:35 CST
**Tester Agent ID**：cursor-tester

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户按启动说明打开前端页面后，能完成客户端提问、查看回答、使用测算组件、搜索历史和切换会话。 | PASS | `npm run test:e2e` desktop 视口：新建会话、提问「宁德时代基本面怎么样」、等待 assistant 回复、历史搜索 `E2E_MARKER`、测算组件提问「买入价100情景价120持仓1000测算收益」均完成；mobile 视口跳过窄屏历史搜索但完成提问与测算。 |
| 2 | 用户切换到管理端后，能查看同一会话、Trace 时间线、Trace 节点展开和完整 JSON 弹窗。 | PASS | `regression.mjs:83` 已改为 `getByRole('heading', { name: 'Trace 链路' })`，无 strict mode 冲突；`.trace-step` 点击、JSON 弹窗打开/关闭均执行成功（desktop + mobile）。 |
| 3 | 用户打开数据说明页和系统设置页，能看见数据源、模型、Prompt 和合规规则状态，且没有真实密钥泄露。 | PASS | E2E 断言 `RAG 状态`、`Prompt 模块` 可见；设置页 `innerText` 无 `sk-`/`Bearer ` 模式；`docs/startup.md`、`.sdd/experience.md`、报告文件无真实 Key；`test_api_regression.py` 含同等断言。 |
| 4 | 用户在 1440x900 和 390x844 两种窗口尺寸下浏览主要页面，输入框、历史列、Trace 面板、表格和按钮均不遮挡、不溢出。 | PASS | 双视口均输出 `PASS viewport desktop/mobile`；`assertNoOverflow` 全程未抛错。 |
| 5 | 当外部 Key、知识库路径或 LangGraph 流转图尚未提供时，最终报告明确说明哪些能力仅完成 fallback 验收。 | PASS | `docs/startup.md` §外部服务配置字段、§当前未完成真实联调的能力清单完整；本报告「外部服务验收范围」同步声明。 |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | `cd frontend && npm run type-check && npm run lint && npm run build` | PASS | 三项均 exit 0。 |
| 2 | `$PY -m ruff check backend/src backend/tests` | PASS | All checks passed。 |
| 3 | `$PY -m mypy backend/src backend/tests` | PASS | Success: no issues found in 33 source files。 |
| 4 | `$PY -m pytest backend/tests` | PASS | 13 passed；`test_api_regression.py` 使用隔离库与 `trust_env=False`。 |
| 5 | 后端 8099 + 前端 5199 短时启动，`VITE_USE_MOCK=false` 全链路回归 | PASS | 短时启动 uvicorn@8099、`VITE_USE_MOCK=false npm run dev`@5199；`npm run test:e2e` exit 0，输出双视口 PASS 与 `E2E regression passed`。 |
| 6 | Vite `/api` 代理指向 8099；`VITE_API_BASE_URL=/api` | PASS | `frontend/.env` 为 `/api`；`vite.config.ts` 默认 `VITE_BACKEND_PROXY_TARGET=http://localhost:8099`；E2E 观测到经 `http://127.0.0.1:5199/api/...` 的代理请求。 |
| 7 | 浏览器自动化覆盖 1440×900 与 390×844，固定高度容器无溢出 | PASS | `VIEWPORTS` 双尺寸均完整执行 `runFlow`。 |
| 8 | 各功能首次真实 API 联调证据来自 T-003～T-007 报告 | PASS | `test-T-003.md`～`test-T-007.md` 均为 PASS；`docs/startup.md:165-171` 已引用。 |
| 9 | `docs/startup.md` 含环境、启动命令、Mock/真实 API 模式、外部服务字段、未完成真实联调清单 | PASS | 章节完整：环境要求、依赖、端口、后端/前端配置、模式一 Mock、模式二 fallback、外部服务表、未完成清单、质量门禁、E2E 说明、FAQ。 |

## 代码与产物检查

| 文件 | 结果 | 说明 |
|------|------|------|
| `docs/startup.md` | PASS | 已创建，无真实密钥，内容完整。 |
| `frontend/e2e/regression.mjs` | PASS | 第 83 行使用 `getByRole('heading', { name: 'Trace 链路' })` 修复上轮 strict mode 问题；双视口全链路可跑通。 |
| `frontend/package.json` | PASS | 含 `playwright` devDependency 与 `test:e2e` 脚本。 |
| `backend/tests/test_api_regression.py` | PASS | 隔离 DB、`app.dependency_overrides`、全链路 API smoke、`trust_env=False`；无 TODO/FIXME。 |
| `.sdd/experience.md` | PASS | 已追加 T-008 经验，无密钥泄露。 |

## 第 2 次验收与上轮对比

| # | 上轮问题 | 状态 |
|---|----------|------|
| 1 | `getByText('Trace 链路')` strict mode 双匹配 | 已修复（`regression.mjs:83`） |
| 2 | E2E 未跑完（测算组件、设置页、mobile 视口） | 已修复（全链路 exit 0） |

## 测试数据库隔离

pytest 全量执行后，运行时库 `backend/data/smart_investment.db` 仍含表：`investment_messages`、`investment_sessions`、`investment_traces`、`layout_preferences`、`users`。未发现测试清空业务库。

## 外部服务验收范围（均为 fallback，非真实完整联调）

| 服务 | 本任务验证方式 | 结论 |
|------|----------------|------|
| 硅基流动 LLM / DeepSeek | `docs/startup.md` + T-004/T-007 报告引用 | fallback only |
| 硅基流动 Embedding / 千问 | 同上 + T-006/T-007 | fallback only |
| 硅基流动 Rerank / 千问 | 同上 + T-006/T-007 | fallback only |
| 本地 Markdown 知识库 | 同上 | fallback only |
| 本地 Mock 行情/财务/公告/宏观 | `test_api_regression.py` 断言 `mock_data` | 已确认（内置示例） |
| LangGraph | 同上 + T-005/T-007 | fallback only |

## E2E 执行证据

```
> frontend@0.0.0 test:e2e
> node e2e/regression.mjs

PASS viewport desktop (1440x900)
PASS viewport mobile (390x844)
E2E regression passed
```

前置：短时启动后端 `GET /api/health` 200；前端 `VITE_USE_MOCK=false` @ 5199 返回 200；`npx playwright install chromium` 已就绪。
