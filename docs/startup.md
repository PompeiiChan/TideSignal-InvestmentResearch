# 智能投研 — 本地启动说明

本文档说明如何在本地启动前后端、切换 Mock / 真实 API fallback 模式，以及外部服务配置与当前能力边界。

> **敏感信息红线**：真实 API Key、Token、Secret 只能写入 `backend/.env` 或 `frontend/.env.local`。本文档及任何 `docs/**`、`.sdd/**` 产物只记录字段名与配置状态，不出现真实值。

## 环境要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.11+（当前项目 `.venv` 为 3.13.5） | 后端与质量门禁 |
| Node.js | 18+（建议 LTS） | 前端 Vite 开发与 E2E |
| npm | 随 Node 安装 | 前端依赖与脚本 |

项目根目录需同时包含 `pycore/`、`backend/`、`frontend/`。后端运行与测试通过 `PYTHONPATH=..` 引入 `pycore`，**不要**对仓库根目录做 editable install。

## 依赖安装

在项目根目录执行：

```bash
# Python 虚拟环境与后端依赖（若尚未创建）
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 前端依赖
cd frontend && npm install
```

约定变量（下文命令均从**项目根**执行）：

```bash
export PY="$(pwd)/.venv/bin/python"
```

## 端口约定

| 场景 | 前端端口 | 后端端口 | 说明 |
|------|----------|----------|------|
| Agent / Tester 自动验证 | **5199** | **8099** | 默认开发联调 |
| 用户门禁验收 | **5175** | **8003** | 通过环境变量切换代理目标 |

前端请求统一使用相对路径 `VITE_API_BASE_URL=/api`，由 Vite 代理到后端，**禁止**在 `.env` 中写完整后端 URL（避免 CORS）。

用户门禁切换示例：

```bash
# 前端代理指向用户门禁后端
VITE_BACKEND_PROXY_TARGET=http://localhost:8003 npm run dev -- --host 127.0.0.1 --port 5175

# 后端使用 8003 端口（需在 backend/.env 或 backend/config/app.toml 中设置 PORT=8003）
cd backend && PYTHONPATH=.. $PY scripts/run_dev.py
```

## 后端配置

1. 复制示例配置：

```bash
cp backend/.env.example backend/.env
```

2. 按需编辑 `backend/.env` 与 `backend/config/app.toml`。运行时以 `ConfigManager` 加载，敏感值只进 `.env`。

3. **LangGraph 编排（T-012，Chat 必需）**：在 `backend/.env` 中设置：

```env
LANGGRAPH_ENV=local
```

同时配置 LLM 意图识别与主输出 Key（`LLM_INTENT_*`、`LLM_*`）。`LANGGRAPH_ENV` 留空或非 `local` 时，`POST /api/chat/query` 返回 **503**（`LangGraph 未就绪，请设置 LANGGRAPH_ENV=local`）；工程状态见 `GET /api/config/status` → `data.orchestration`。

修改 `LANGGRAPH_ENV` 或 LLM 相关字段后，**须重启后端**（8099）方可生效。

4. 首次或 schema 变更后，确保 SQLite 数据目录存在（`backend/data/`）；服务启动时会按 pycore 模板初始化表结构。

### 启动后端（自动验证端口 8099）

```bash
cd backend && PYTHONPATH=.. $PY scripts/run_dev.py
```

或等价命令：

```bash
cd backend && PYTHONPATH=.. $PY -m uvicorn src.main:app --host 127.0.0.1 --port 8099
```

健康检查：

```bash
curl --noproxy '*' http://127.0.0.1:8099/api/health
```

短时 smoke（不长期占用端口）：

```bash
cd backend && PYTHONPATH=.. $PY scripts/smoke_health.py
```

## 前端配置

默认 `frontend/.env`：

```env
VITE_API_BASE_URL=/api
VITE_USE_MOCK=true
VITE_BACKEND_PROXY_TARGET=http://localhost:8099
```

`frontend/vite.config.ts` 将 `/api` 与 `/ws` 代理到 `VITE_BACKEND_PROXY_TARGET`（默认 `http://localhost:8099`）。

## 模式一：前端 Mock MVP（无需后端）

适用于 UI/UX 验收或纯前端开发。

1. 确认 `frontend/.env` 中 `VITE_USE_MOCK=true`。
2. 启动前端：

```bash
cd frontend && npm run dev -- --host 127.0.0.1 --port 5199
```

3. 浏览器打开 `http://127.0.0.1:5199/client`。

此模式下数据来自 `frontend/src/mocks/`，不调用真实后端。

## 模式二：真实 API + V1.1 真实 AI（推荐联调与 E2E）

适用于 V1.1 真实 LLM / Embedding / Rerank / LangGraph 全链路。须先配置 `backend/.env` 中硅基流动 Key 与 `LANGGRAPH_ENV=local`。

1. **先启动后端**（8099）。
2. 确认 `frontend/.env`：

```env
VITE_USE_MOCK=false
VITE_API_BASE_URL=/api
VITE_BACKEND_PROXY_TARGET=http://localhost:8099
```

3. 启动前端：

```bash
cd frontend && npm run dev -- --host 127.0.0.1 --port 5199
```

4. 验证：`GET /api/config/status` 中 LLM / Embedding / Rerank / LangGraph 均为 `ready`；浏览器请求走 `http://127.0.0.1:5199/api/...` 代理到 8099。

### 主要页面路由

| 路由 | 说明 |
|------|------|
| `/client` | 客户端对话 |
| `/client/data` | 数据说明（客户端入口） |
| `/admin` | 管理端对话 + Trace 面板 |
| `/admin/data` | 数据说明 |
| `/admin/settings` | 系统设置（仅管理端） |

侧栏底部可切换「客户端 / 管理端」。

## 外部服务配置字段

以下字段在 `backend/.env.example` 中定义；真实值只写入 `backend/.env`。页面与 `GET /api/config/status` **只返回字段名、状态与缺失项**，不返回密钥内容。

| 服务 | 配置字段 | V1.1 必需 | 当前状态（Key 已配且后端已重启时） |
|------|----------|----------|-----------------------------------|
| 硅基流动 LLM / 意图识别 | `LLM_INTENT_API_KEY`, `LLM_INTENT_BASE_URL`, `LLM_INTENT_MODEL` | 是 | **ready**（真实调用） |
| 硅基流动 LLM / 主输出 | `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | 是 | **ready**（真实调用） |
| 硅基流动 Embedding / 千问 | `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM` | 是 | **ready**（混合检索） |
| 硅基流动 Rerank / 千问 | `RERANK_API_KEY`, `RERANK_BASE_URL`, `RERANK_MODEL` | 是 | **ready**（RAG 重排） |
| 本地 Markdown 知识库 | `LOCAL_KB_PATH` | 是 | **已接入**（`data/knowledge-base/`，约 87 个 `.md`，索引 v6） |
| 本地 Mock 行情 / 财务 / 公告 / 宏观 | `MOCK_DATA_PATH` | 是（问数/工具） | 已确认 |
| LangGraph Agent 编排 | `LANGGRAPH_ENV=local` | 是 | **ready**（Chat 默认路径，非 fallback） |

页面与 `GET /api/config/status` **只返回字段名、状态与缺失项**，不返回密钥。若某项为 `missing` 或 Chat 返回 503，按缺失字段补全 `backend/.env` 并**重启后端**。

### V1.1 各能力首次真实联调证据

| 能力 | 任务 | 报告 |
|------|------|------|
| LLM 真实调用 | T-009 | `.sdd/test-reports/T-009-report.md` |
| Embedding + 知识库 RAG | T-010 | `.sdd/test-reports/T-010-report.md` |
| Rerank 重排 | T-011 | `.sdd/test-reports/test-T-011.md` |
| LangGraph 编排 | T-012 | `.sdd/test-reports/test-T-012.md` |
| **V1.1 全链路回归** | T-013 | `.sdd/test-reports/test-T-013.md` |

MVP 阶段报告（T-001～T-008）仍保留作 UI / API 契约参考。

## 当前未完成真实联调的能力清单

**V1.1 核心 AI 能力（LLM、Embedding、Rerank、本地知识库 RAG、LangGraph）已在 T-009～T-012 完成首次真实联调；T-013 做全系统回归收口。**

仍属 **MVP 演示或后续版本**、不在 V1.1 收口范围：

1. **第三方真实金融行情/财务 API** — 问数/问股工具仍主要使用本地 Mock 与公开页解析，非券商级实时行情。
2. **多账号登录 / SSO** — 未做。
3. **Query 改写、多轮记忆、Live Tool** — V1.2+ backlog（T-014～T-018）。
4. **知识库持续扩容** — T-019 创业板 50 家入库进行中，与 V1.1 回归可并行。

客户端与管理端**可见 UI 不展示**「Agent fallback」「真实 LLM 未接入」等内部工程文案；工程边界见 Trace 与 `.sdd/test-reports/`。

## 质量门禁

### 后端

```bash
$PY -m ruff check backend/src backend/tests
$PY -m mypy backend/src backend/tests
$PY -m pytest backend/tests
```

### 前端

```bash
cd frontend && npm run type-check
cd frontend && npm run lint
cd frontend && npm run build
```

## E2E 全链路回归

前置条件：**后端 8099 已启动**，前端以 `VITE_USE_MOCK=false` 运行在 **5199**。

1. 安装 Playwright 浏览器（首次）：

```bash
cd frontend && npx playwright install chromium
```

2. 执行回归脚本（覆盖 1440×900 与 390×844 视口、主要页面与 API 代理）：

```bash
cd frontend && npm run test:e2e
```

可选环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `E2E_BASE_URL` | `http://127.0.0.1:5199` | 前端地址 |
| `E2E_API_BASE` | `http://127.0.0.1:5199/api` | 经 Vite 代理的 API |
| `E2E_ASSISTANT_TIMEOUT_MS` | `180000` | 等待真实 LLM 首条回复（毫秒） |
| `E2E_CLEANUP` | `true` | 结束后删除 E2E 创建的会话 |

脚本会检查横向溢出（`scrollWidth <= viewportWidth`），并遍历客户端提问、历史搜索、管理端 Trace、数据说明与系统设置页。

> E2E 覆盖双视口布局、真实 API 代理、客户端提问与管理端 Trace/设置。全链路 AI 四类用例（热点/问数/问股/文档）见 T-013 回归报告；**不替代** T-009～T-012 各任务内的首次真实联调记录。

## 常见问题

**本地 curl 被代理劫持**  
对 `127.0.0.1` 使用 `curl --noproxy '*'`。

**`VITE_USE_MOCK=false` 仍像 Mock**  
确认已重启 Vite dev server；检查 `frontend/.env` 与启动命令中的环境变量。

**pytest 后业务库被清空**  
测试应使用隔离库夹具；若污染演示数据，从备份恢复 `backend/data/smart_investment.db` 或重新 seed。

**端口占用**  
自动验证使用 5199/8099；用户门禁使用 5175/8003，勿与自动验证端口混用同一验收轮次。
