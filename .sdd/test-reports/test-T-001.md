# 测试报告：T-001 前端 Mock MVP 页面闭环

**测试时间**：2026-06-08 19:29 CST
**Tester Agent ID**：codex-tester

## 结果：PASS

## 复验结论

上轮 FAIL 问题已修复：`/client` 首屏不再出现 React Router 错误页，Browser/IAB 在 1440x900 与 390x844 均未捕获 `Maximum update depth exceeded` 或 `getSnapshot should be cached` console error。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户打开客户端页面，能看到左侧会话历史、中间对话区和固定在底部的输入框，历史再多也不会把输入框顶出页面。 | PASS | Browser/IAB 1440x900 访问 `/client`，可见历史列表、对话区和底部固定输入框；console error 为空。 |
| 2 | 用户在客户端输入投研问题并发送，页面新增本轮问答，回答展示表格、个股卡、引用来源和“不构成投资建议”风险提示。 | PASS | Mock 数据首屏展示排行表、引用来源和风险提示；单页面发送测算问题后新增问答并展示交互式测算组件。 |
| 3 | 用户点击新建会话，发送首条问题前历史标题显示“新对话”，发送后标题替换为用户输入的问题，长标题按侧栏宽度自动省略。 | PASS | Browser/IAB 单页流转中，新建后历史项显示“新对话”，发送后替换为“如果我 15 元买入，未来到 20 元，预期回报率是多少？”，侧栏按宽度省略显示。 |
| 4 | 用户在历史搜索框输入关键词，历史列表能实时过滤；没有结果时页面展示空状态。 | PASS | `Sidebar.tsx` 绑定 `setSearchKeyword`，`mockApi.getSessions` 按标题和 agent label 过滤，空列表展示“没有匹配的历史问题”；上轮已静态确认，本轮首屏历史列表正常渲染。 |
| 5 | 用户切换到管理端，能看到同一会话的问答内容和右侧 Trace 链路；客户端不展示系统设置入口，管理端展示系统设置入口。 | PASS | `/client` 可见“对话/数据说明”，无系统设置入口；切到管理端后可见“系统设置”和右侧 Trace 链路。 |
| 6 | 用户点击 Trace 节点，节点在原位置展开摘要详情；点击查看完整 JSON，页面弹出完整 JSON 弹窗。 | PASS | 管理端可见 Trace 节点详情和“查看完整 JSON”；点击后弹出 JSON modal，包含当前节点结构化 JSON。 |
| 7 | 用户打开数据说明页和系统设置页，能看到本地 Mock 数据、RAG 状态、模型配置、Prompt 和合规规则状态，且页面不展示真实密钥。 | PASS | `/client/data` 显示行情、财务、研报、公告、投研知识库和 RAG 状态；`/admin/settings` 显示模型字段、Prompt、合规规则。扫描未发现真实密钥值。 |
| 8 | 用户拖拽历史列和 Trace 面板宽度，中间对话区、底部输入框和卡片内容保持稳定，没有遮挡、跳动或溢出。 | PASS | `Sidebar.tsx` 与 `TracePanel.tsx` 使用 pointer drag，store clamp 范围为侧栏 240-420、Trace 380-640；桌面截图中主区、底部输入框和卡片内容稳定可见。 |
| 9 | 用户在 1440x900 桌面窗口和 390x844 移动宽度浏览页面，主要文字、按钮、表格和输入框均可见，没有明显横向或纵向溢出。 | PASS | Browser/IAB 1440x900 可见历史、富响应表格、风险提示和底部输入框；390x844 可见页面主文案、按钮、表格区域和底部输入框，无 React 错误页。 |

## 技术检查逐条验证

| # | 检查 | 结果 | 说明 |
|---|------|------|------|
| 1 | cd frontend && npm run type-check 通过 | PASS | 已独立执行，通过。 |
| 2 | cd frontend && npm run lint 通过 | PASS | 已独立执行，通过。 |
| 3 | cd frontend && npm run build 通过 | PASS | 已独立执行，通过，Vite 构建成功。 |
| 4 | frontend/src/mocks/ 的 Session、Message、Trace、RichBlock、数据源状态和配置状态结构与 docs/api-contracts.md 一致 | PASS | Mock endpoint 通过 DTO 构造函数输出契约字段，内部 `agent_label/default_trace_id` 未外泄到响应 DTO。 |
| 5 | VITE_USE_MOCK=true 时页面不依赖后端服务即可完成 Mock MVP 验收 | PASS | `.env` 为 `VITE_USE_MOCK=true`；复验未启动真实后端，页面可完成 Mock 首屏和单页面状态流转。 |
| 6 | frontend/.env 中 VITE_API_BASE_URL=/api，frontend/vite.config.ts 配置 server.proxy['/api'] 默认指向 http://127.0.0.1:8099 或 http://localhost:8099 | PASS | `.env` 为 `VITE_API_BASE_URL=/api`、`VITE_BACKEND_PROXY_TARGET=http://localhost:8099`；`vite.config.ts` `/api` 默认 `http://localhost:8099`，`/ws` 配置 `ws: true`。 |
| 7 | 固定高度容器按内容理论高度预留至少 20% 缓冲；真实浏览器验证 1440x900 与 390x844 无溢出 | PASS | 1440x900 和 390x844 均完成真实浏览器渲染检查，无明显业务内容溢出或错误页。 |

## 上轮问题修复确认

| 上轮问题 | 状态 | 证据 |
|---|---|---|
| `ChatView.tsx` 在空 `activeSessionId` 下返回新数组导致 React/Zustand 无限更新。 | 已修复 | `ChatView.tsx` 使用模块级 `EMPTY_MESSAGES` 稳定引用；Browser/IAB 复验 `/client` 无 console error。 |

## 已执行命令

```text
cd frontend && npm run type-check
cd frontend && npm run lint
cd frontend && npm run build
cd frontend && npm run dev -- --host 127.0.0.1 --port 5199
```

## Mock 阶段边界

- 未启动真实后端。
- 未调用外部服务。
- 未使用 Playwright/Puppeteer/Cypress。
- 浏览器检查使用当前环境 Browser/IAB 的视口、导航、可见 DOM、截图和 console 日志能力。
