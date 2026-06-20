# Demo 公网部署（Vercel 前端 + Railway 后端）

本文说明如何将 TideSignal 智能投研 Demo 部署到公网，并启用**访客每日 5 次提问**额度。

## 架构

```text
用户浏览器
    → Vercel（静态前端，Vite SPA）
    → Railway（FastAPI 后端 + SQLite + 知识库）
```

- 前端通过 `VITE_API_BASE_URL` 指向 Railway 公网 API。
- 浏览器 `localStorage` 生成访客 UUID，请求头携带 `X-Demo-Visitor-Id`。
- 后端按访客 ID + 客户端 IP 哈希计数，超额返回 HTTP 429。

## 一、Railway 部署后端

### 1. 新建项目

1. 登录 [Railway](https://railway.app)，从 GitHub 导入本仓库。
2. 根目录已包含 `Dockerfile` 与 `railway.toml`，Railway 会自动构建。
3. 健康检查路径：`GET /api/health`。

### 2. 环境变量（Variables）

在 Railway Service → Variables 中配置（**勿将真实密钥提交 Git**）：

| 变量 | 示例 / 说明 |
|------|-------------|
| `HOST` | `0.0.0.0` |
| `PORT` | Railway 自动注入，无需手写 |
| `APP_CONFIG_PATH` | `config/app.toml` |
| `LANGGRAPH_ENV` | `local` |
| `DEMO_QUOTA_ENABLED` | `true` |
| `DEMO_QUOTA_DAILY_LIMIT` | `5` |
| `DEMO_QUOTA_IP_DAILY_LIMIT` | `20`（同 IP 防刷，可按需调整） |
| `MOCK_DATA_PATH` | `data/mock` |
| `LOCAL_KB_PATH` | `data/knowledge-base` |
| `CORS_ORIGINS` | `["https://<你的-vercel-域名>.vercel.app"]` |
| `LLM_API_KEY` / `LLM_INTENT_API_KEY` / `EMBEDDING_API_KEY` 等 | 硅基流动或其它供应商密钥 |

> `CORS_ORIGINS` 必须是 JSON 数组字符串。部署自定义域名后记得同步更新。

### 3. 持久化（可选）

默认 SQLite 写在容器内 `backend/data/smart_investment.db`。容器重建会丢失会话与额度计数。Demo 可接受；若需持久化，请挂载 Railway Volume 到 `/app/backend/data`。

### 4. 验证

部署完成后访问：

```text
https://<railway-domain>/api/health
```

应返回 `{"code":200,"data":{"status":"ok"},...}`。

## 二、Vercel 部署前端

### 1. 新建项目

1. 登录 [Vercel](https://vercel.com)，导入同一 GitHub 仓库。
2. **Root Directory** 设为 `frontend`。
3. Framework Preset：`Vite`。
4. Build Command：`npm run build`（默认即可）。
5. Output Directory：`dist`。

`frontend/vercel.json` 已配置 SPA fallback（所有路由回 `index.html`）。

### 2. 环境变量

| 变量 | 值 |
|------|-----|
| `VITE_API_BASE_URL` | `https://<railway-domain>/api` |

注意：末尾是 `/api`，与本地 Vite proxy 行为一致。

### 3. 验证

打开 Vercel 域名，输入框下方应显示「今日 Demo 剩余 x/5 次提问」（需后端 `DEMO_QUOTA_ENABLED=true`）。

## 三、额度机制说明

| 项 | 行为 |
|----|------|
| 计数范围 | `POST /api/chat/query`、`/query/stream`、`/regenerate/stream` |
| 访客标识 | 前端 `localStorage` UUID → 请求头 `X-Demo-Visitor-Id` |
| 每日上限 | 默认 5 次/访客（`DEMO_QUOTA_DAILY_LIMIT`） |
| IP 上限 | 默认 20 次/IP（`DEMO_QUOTA_IP_DAILY_LIMIT`，0 表示关闭） |
| 重置 | 按 `Asia/Shanghai` 自然日 |
| 查询余额 | `GET /api/demo/quota` |
| 超额 | HTTP 429，前端弹窗提示 |

本地开发默认**不启用**额度（`demo_quota_enabled=false`）。要在本地测试，在 `backend/.env` 设置：

```env
DEMO_QUOTA_ENABLED=true
DEMO_QUOTA_DAILY_LIMIT=5
```

## 四、本地联调（模拟生产）

```bash
# 终端 1：后端
cd Projects_Repo/smart-investment-research
export DEMO_QUOTA_ENABLED=true
export CORS_ORIGINS='["http://localhost:5199"]'
PYTHONPATH=.:backend .venv/bin/python -m uvicorn backend.src.main:app --host 0.0.0.0 --port 8099

# 终端 2：前端（指向本地 API）
cd frontend
VITE_API_BASE_URL=http://127.0.0.1:8099/api npm run dev
```

## 五、常见问题

**CORS 报错**  
检查 Railway `CORS_ORIGINS` 是否包含完整 Vercel 域名（含 `https://`）。

**额度不显示**  
确认 `DEMO_QUOTA_ENABLED=true` 且 `GET /api/demo/quota` 返回 `enabled: true`。

**Chat 503**  
确认 `LANGGRAPH_ENV=local` 且 LLM 密钥已配置。

**镜像过大 / 构建慢**  
知识库在 `backend/data/knowledge-base`，体积较大属正常。可用 `.dockerignore` 排除无关目录（已排除 `frontend/`、`.sdd/` 等）。
