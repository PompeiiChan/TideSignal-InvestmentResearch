# 测试报告：T-002 后端基础设施与本地联调代理

**测试时间**：2026-06-09 00:52 CST
**Tester Agent ID**：codex-tester

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 后端服务可在本地启动，健康检查返回服务正常。 | PASS | 短时 uvicorn smoke 在 `127.0.0.1:8099` 启动成功，`GET /api/health` 返回 `code=200`、`message=success`、`data.status=ok`，脚本自动退出。 |
| 2 | 前端切到真实 API 模式时，浏览器请求会走 /api 代理到后端自动验证端口，而不是直接访问完整后端 URL。 | PASS | `frontend/.env` 保持 `VITE_API_BASE_URL=/api`；`frontend/vite.config.ts` 的 `/api` 代理默认 `http://localhost:8099`，并支持 `VITE_BACKEND_PROXY_TARGET` 临时切到用户门禁后端端口。 |
| 3 | 配置文件只展示字段名和默认状态，不包含真实 Key、Token 或密码。 | PASS | `backend/.env.example` 只包含字段名和空占位；`backend/config/app.toml`、`docs/**`、`.sdd/**` 未发现真实敏感值。 |

## 技术检查逐条验证

| # | 检查 | 结果 | 说明 |
|---|------|------|------|
| 1 | `backend/src/main.py` 使用 `pycore.api.APIServer` 创建服务，不重写已有 pycore server/config/logger 能力。 | PASS | `backend/src/main.py` 使用 `APIServer` + `APIConfig` 创建 app，并注册 PyCore 中间件与健康路由。 |
| 2 | 配置使用 `pycore.core.ConfigManager` 读取显式配置文件，敏感值只允许进入 `.env` / `.env.local`。 | PASS | 实现位于 `backend/src/settings.py`，符合后端规范“不得重写 `backend/src/core/config.py`”的约束。 |
| 3 | `$PY -m ruff check backend/src backend/tests` 通过。 | PASS | `.venv/bin/python -m ruff check backend/src backend/tests` 输出 `All checks passed!`。 |
| 4 | `$PY -m mypy backend/src backend/tests` 通过。 | PASS | `.venv/bin/python -m mypy backend/src backend/tests` 输出 `Success: no issues found in 12 source files`。 |
| 5 | `$PY -m pytest backend/tests` 通过。 | PASS | `.venv/bin/python -m pytest backend/tests` 结果为 `2 passed`；pycore 内部 Pydantic deprecation warnings 不影响本任务。 |
| 6 | `cd backend && PYTHONPATH=.. $PY -m uvicorn src.main:app --host 127.0.0.1 --port 8099` 可短时启动，`GET /api/health` 返回 200 和统一响应格式。 | PASS | 清理旧 8099 监听进程后，`PYTHONPATH=.. ../.venv/bin/python scripts/smoke_uvicorn.py` 通过并返回统一响应 JSON。 |
| 7 | backend CORS 允许 localhost/127.0.0.1 的 5199 与 5175。 | PASS | `backend/config/app.toml` 与默认 settings 包含 `localhost/127.0.0.1` 的 `5199`、`5175`；测试覆盖 `localhost:5199` 预检。 |
| 8 | `frontend/.env` 中 `VITE_API_BASE_URL=/api`；`frontend/vite.config.ts` 的 `/api` 代理默认指向后端自动验证端口 8099。 | PASS | 已静态验证。 |
| 9 | `frontend/vite.config.ts` 支持通过 `VITE_BACKEND_PROXY_TARGET=http://localhost:8003` 临时切换 `/api` 代理到用户门禁后端端口。 | PASS | `vite.config.ts` 从 env 读取 `VITE_BACKEND_PROXY_TARGET`，默认值为 `http://localhost:8099`。 |

## 执行命令

```text
.venv/bin/python -m ruff check backend/src backend/tests
.venv/bin/python -m mypy backend/src backend/tests
.venv/bin/python -m pytest backend/tests
cd backend && PYTHONPATH=.. ../.venv/bin/python scripts/smoke_health.py
cd backend && PYTHONPATH=.. ../.venv/bin/python scripts/smoke_uvicorn.py
```

## 过程说明

- 初次真实端口 smoke 被沙箱网络权限阻止。
- 提权后发现 `127.0.0.1:8099` 被旧 Python 进程占用，且该进程 `/api/health` 返回 FastAPI 默认 404，不是当前 T-002 服务。
- 停止旧监听进程后，T-002 短时 uvicorn smoke 通过。

## Mock / 外部服务边界

- T-002 不依赖真实 LLM、Embedding、Rerank、LangGraph 或金融数据 API。
- 未调用任何外部服务。
- 未写入真实 Key、Token 或 Secret。
