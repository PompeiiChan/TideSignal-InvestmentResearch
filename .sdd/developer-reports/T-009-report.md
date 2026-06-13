# T-009 Developer Report — 硅基流动 LLM 真实接入

## 实现摘要

- 新增 `backend/src/integrations/llm/`：基于 `httpx`（`trust_env=False`）封装硅基流动 OpenAI 兼容 `/chat/completions` 调用。
- `ChatService` 改为串联真实 LLM 意图识别、回答生成、质检合规三步；移除关键词 fallback 回答路径。
- `TraceService.create_llm_trace` 记录 `llm_intent_recognition` / `llm_quality_check` / `llm_response_generation` 节点及模型元数据（不含密钥）。
- `settings.get_settings()` 在 `ConfigManager` 加载 `app.toml` 后叠加 `backend/.env` 中的 `LLM_*` 等字段。
- `GET /api/config/status` 在 `LLM_*` 三字段齐全时自动标记 `ready`（逻辑沿用 `_model_status`）。

## 修改/新增文件

- `backend/src/integrations/__init__.py`
- `backend/src/integrations/llm/__init__.py`
- `backend/src/integrations/llm/client.py`
- `backend/src/integrations/llm/models.py`
- `backend/src/integrations/llm/prompts.py`
- `backend/src/integrations/llm/service.py`
- `backend/src/settings.py`
- `backend/src/services/chat_service.py`
- `backend/src/services/trace_service.py`
- `backend/src/api/routes/chat.py`
- `backend/tests/conftest.py`
- `backend/tests/test_llm_integration.py`
- `backend/tests/test_api_regression.py`
- `backend/tests/test_sessions_layout.py`

## 质量门禁（Developer 已执行）

| 检查项 | 结果 |
|--------|------|
| `ruff check backend/src backend/tests` | PASS |
| `mypy backend/src backend/tests` | PASS |
| `pytest backend/tests` | 17 passed, 1 skipped |
| `npm run type-check` | PASS |
| `npm run lint` | PASS |
| `npm run build` | PASS |

## 如何验证（Tester / 用户）

### 1. 配置

在 `backend/.env` 写入（真实值仅放配置文件）：

```env
LLM_API_KEY=<硅基流动 Key>
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_MODEL=<模型名，如 deepseek-ai/DeepSeek-V3>
```

### 2. 启动

```bash
cd backend && PYTHONPATH=.. .venv/bin/python scripts/run_dev.py
cd frontend && VITE_USE_MOCK=false npm run dev -- --port 5199
```

### 3. 终端 smoke

```bash
# 配置状态：LLM 应为 ready，响应中不得出现 sk- / Bearer
curl --noproxy '*' http://127.0.0.1:8099/api/config/status

# 新建会话并提问
SESSION=$(curl --noproxy '*' -s -X POST http://127.0.0.1:8099/api/sessions \
  -H 'Content-Type: application/json' -d '{"source":"client"}' | jq -r '.data.id')
curl --noproxy '*' -s -X POST http://127.0.0.1:8099/api/chat/query \
  -H 'Content-Type: application/json' \
  -d "{\"session_id\":\"$SESSION\",\"source\":\"client\",\"query\":\"机器人板块最近有哪些政策催化\"}"
```

预期：200；`assistant_message.content` 为模型生成文案；`rich_blocks` 含结构化块、引用与风险提示；Trace summary `quality_check_result` 为 PASS/FAIL；无“演示级链路”“真实 LLM 未接入”等内部词。

### 4. 浏览器

1. `frontend/.env` 设 `VITE_USE_MOCK=false`
2. 打开 `http://127.0.0.1:5199/client`，新建会话提问
3. 首条问题后标题应从「新对话」变为问题内容
4. 管理端同会话 Trace 中意图识别/回答生成节点应展示模型名与 latency，不含密钥
5. 系统设置页 LLM 行 `status=ready`，仅字段名

### 5. 可选真实上游单测

```bash
REAL_API_TEST=1 .venv/bin/python -m pytest backend/tests/test_llm_integration.py::test_real_siliconflow_llm_call -q
```

## 已知限制（T-010 前）

- **无 RAG**：回答由 LLM 直接生成，引用来源为「模型整理」类标注；Trace RAG 节点 `rag_hits=[]`，待 T-010 接入本地知识库检索。
- **工具调用仍为本地占位**：行情/财务数据工具未接真实 API，Trace 工具节点描述本地占位逻辑。
- **LangGraph 未接入**：路由为 LLM 意图结果，非 StateGraph 编排（T-012）。
- **LLM 未配置时**：`POST /api/chat/query` 返回 503；单元测试通过 `conftest` mock，不依赖真实 Key。

## 真实外部服务联调

Developer 环境无 `backend/.env`（gitignore），未能在此会话执行真实硅基流动调用。Tester 在 Key 已配环境必须完成真实调用验收，不得以 mock/fallback 判 PASS。
