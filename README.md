# 潮声 TideSignal · 智能投研

面向散户与投顾的 **A 股智能投研对话** Web 应用：自然语言问热点、问股、问数、读文档，支持流式回答与可交互富组件（排行表、板块热力图、收益率测算器等）。

本仓库是业务项目 **`smart-investment-research`** 的独立 Git 仓库，**不包含**上层 SDD Harness（`harness-core/`、Harness 根目录规则等）。本地若使用 Harness 开发，请在 Harness 工作区中打开上层目录，业务代码仍写在本项目路径下。

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 19 + TypeScript + Vite + Ant Design |
| 后端 | Python 3.11+、FastAPI（PyCore）、LangGraph 编排 |
| 数据 | SQLite（会话/消息/Trace）、本地知识库 RAG |
| 外部 | SiliconFlow LLM、东财/腾讯行情、同花顺热点等 |

## 仓库结构

```text
smart-investment-research/
├── backend/          # FastAPI + LangGraph Agent 链路
├── frontend/         # 客户端 / 管理端 UI
├── pycore/           # 共享框架（API、LLM、DB 适配）
├── docs/             # PRD、API 契约、启动说明、Agent 文档
├── .sdd/             # 任务状态、测试报告、经验沉淀（SDD 产物）
└── third_party/      # 第三方数据脚本等
```

## 快速启动

详细步骤见 [`docs/startup.md`](docs/startup.md)。默认开发端口：**前端 5199**，**后端 8099**。

```bash
# 1. 依赖
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cd frontend && npm install && cd ..

# 2. 配置
cp backend/.env.example backend/.env
# 编辑 backend/.env：LANGGRAPH_ENV=local，并填写 LLM 相关 Key

# 3. 启动后端
cd backend && PYTHONPATH=.. ../.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8099

# 4. 启动前端（另开终端，项目根目录）
cd frontend && npm run dev -- --host 127.0.0.1 --port 5199
```

浏览器访问：http://127.0.0.1:5199

前端通过 `VITE_USE_MOCK=false` 与 Vite 代理 `/api` → `8099` 联调真实后端（见 `frontend/.env`）。

## 核心能力

### V1.1（`ed52d93`）

- **问热点 / 问股 / 问数 / 文档问答**：LangGraph 意图识别 → 路由 → RAG + 工具链 → 流式组装回答
- **富组件**：`ranking_table`、`sector_heatmap`、`calculator`、`scenario_calculator`
- **Trace 可观测**：管理端查看节点级执行链路
- **本地知识库**：财报、研报等 RAG 检索（`backend/data/knowledge-base/`）

### V1.2 及后续（当前 `main`）

在 V1.1 基础上已落地（详见 `.sdd/test-reports/` 与各任务 completion 报告）：

- **回答过程时间线**（T-020）：流式开始前可折叠的执行过程展示
- **问数 / 问股 / 热点深化**（T-021～T-024）：估值分位、财务深度、热点工具丰富度、KB ingest 刷新
- **多轮对话**（T-015～T-017）：五轮短期记忆、槽位继承、下游上下文注入
- **Query 改写**（T-014 / T-014-P2）：检索 query passthrough + 维度多路检索
- **问股 live 基本面 Tool**（T-018）：新浪财报、同花顺一致预期、东财研报元数据、巨潮公告；Trace 含数据来源归因

左侧历史示例会话（排行表 / 测算器 / 热力图）在首次拉列表时自动置顶，便于验收富组件。

## 文档索引

| 文档 | 说明 |
|------|------|
| [`docs/startup.md`](docs/startup.md) | 本地启动、端口、Mock、外部服务 |
| [`docs/api-contracts.md`](docs/api-contracts.md) | HTTP API 契约 |
| [`docs/agent/README.md`](docs/agent/README.md) | Agent / LangGraph 说明 |
| [`docs/agent/response-bad-case.md`](docs/agent/response-bad-case.md) | 回答质量 Bad Case 与修复记录 |

## 版本检查点（回滚用）

| 代号 | 提交 | 说明 |
|------|------|------|
| **V1.1** | `ed52d93` | 流式输出、富组件示例与侧栏标签、年报澄清修复（BC-007）等 |
| **V1.2** | `7485f74` | 回答过程时间线、问数 P1 真实 API、移除问数 Mock 等 |
| **V1.2+（当前）** | `75aa4ec` | 多轮记忆（T-015～T-017）、Query 改写（T-014）、问股 live Tool（T-018）、热点/财务深化与 KB 扩容（T-021～T-024） |

回滚到某一检查点（**会丢弃之后所有本地未推送改动，慎用**）：

```bash
git fetch origin
git reset --hard <提交哈希>   # 例如 ed52d93、7485f74、75aa4ec
```

当前 `main` 与 `origin/main` 对齐在 **`75aa4ec`**。

## 许可证与免责

本项目为投研信息整理与参数测算工具，**不构成投资建议**。行情与研报引用以正文及参考来源为准。
