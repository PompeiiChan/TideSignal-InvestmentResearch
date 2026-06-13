# 测试报告：T-009 硅基流动 LLM 真实接入

**测试时间**：2026-06-11（第 3 轮）
**Tester Agent ID**：cursor-tester

## 结果：PASS（第 4 轮修复后，2026-06-11）

第 3 轮 FAIL 根因：Qwen3.5 意图模型需在请求体**顶层**设置 `enable_thinking: false`（仅 `chat_template_kwargs` 无效）。修复后：

- `REAL_API_TEST=1` 意图识别单测 PASS
- `POST /api/chat/query` 全链路 200（~28s），标题替换、富响应 blocks 正常
- 配置：意图 `Qwen/Qwen3.5-9B` + 独立 Key；主输出 `Qwen/Qwen3.5-27B` + 独立 Key

---

## 结果（第 3 轮归档）：FAIL

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 客户端提问展示真实模型回答（结构化内容、引用、风险提示；无内部工程文案） | **FAIL** | `POST /api/chat/query` 返回 **502**，`message: LLM 返回内容无法解析为 JSON`（~22s）；Playwright 双视口发送问题后 `assistantVisible=false`，页面 `pageerror: Request failed with status code 502`，未展示助手回答 |
| 2 | 新会话首条问题后标题从「新对话」替换为问题内容 | **FAIL** | 问答链路在意图识别 JSON 解析阶段失败，会话标题保持「新对话」 |
| 3 | 管理端 Trace 展示真实 LLM 意图识别/回答生成节点（无密钥） | **FAIL** | 失败请求未持久化 Trace；`GET /api/traces?session_id=...` 返回 0 条 |
| 4 | 系统设置页展示 LLM 字段名与 ready 状态，不展示密钥 | **PASS** | Playwright 双视口（1440×900 / 390×844）访问 `/admin/settings`：`LLM_INTENT_*` 与 `LLM_*` 字段名可见，状态为 ready，无 `sk-` 密钥样式内容，无横向溢出 |

## technicalChecks 逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | ruff check backend/src backend/tests | PASS | `All checks passed!` |
| 2 | mypy backend/src backend/tests | PASS | `Success: no issues found in 41 source files` |
| 3 | pytest backend/tests | PASS | `20 passed, 1 skipped`（第 2 轮 `test_health` 硬编码 mocked 问题已修复） |
| 4 | frontend type-check / lint / build | PASS | 三项均 exit 0 |
| 5 | LLM_* 从 backend/.env 读取，未硬编码 | PASS | 意图识别 `LLM_INTENT_*`、主输出 `LLM_*` 均从 `.env` 加载；`sk-` 扫描响应与页面无泄露 |
| 6 | httpx trust_env=False | PASS | `client.py:69` |
| 7 | VITE_USE_MOCK=false 真实联调 POST /api/chat/query | **FAIL** | 经 Vite 代理（15199→18199）`POST /api/chat/query` 命中真实后端，返回 502 |
| 8 | frontend/.env `/api`；vite 代理 8099 | PASS | `VITE_API_BASE_URL=/api`；`vite.config.ts` 默认 `http://localhost:8099`；本轮因 8099 被 `auto-cs` 占用，联调使用 `18199/15199` |
| 9 | GET /api/config/status 意图识别与主输出均 ready | PASS | 两项 `status=ready`，`missing_fields=[]` |
| 10 | 真实硅基流动 LLM 调用验收 | **FAIL** | `REAL_API_TEST=1 pytest test_real_siliconflow_llm_call` → `LLMClientError: LLM 返回内容无法解析为 JSON` |
| 11 | 外部服务失败清晰错误处理 | PASS | 502 返回明确消息；服务端日志记录 `Failed to parse LLM JSON payload` |
| 12 | 双视口 1440×900 / 390×844 无溢出 | **部分** | 设置页双视口无横向溢出；含真实回答气泡的溢出检查未执行（问答失败） |

## 如果 FAIL，详情如下

### 问题 1：Qwen3.5 推理模型 reasoning_content 为思考过程文本，无法解析为 JSON

- **标准**：#1、#10、真实 LLM 联调
- **现象**：意图识别模型 `Qwen/Qwen3.5-9B`。虽已设置 `chat_template_kwargs.enable_thinking=false` 且 `max_tokens=1024`，上游仍将思考过程写入 `reasoning_content`（以 `Thinking Process:` 开头），`content` 为空或不含 JSON。`extract_message_content` 回退读取 `reasoning_content` 后，`_parse_json_payload` 无法从中提取合法 JSON，全链路 502。
- **位置**：`backend/src/integrations/llm/client.py:62-66,102-114`；`backend/src/integrations/llm/service.py:97-108,210-233`
- **建议修复方向**：
  1. 意图识别改用非推理模型（如 `deepseek-ai/DeepSeek-V3`）作为 `LLM_INTENT_MODEL`；
  2. 或在 `_parse_json_payload` 中增强从 reasoning 文本末尾提取 JSON 块的能力，并确保 token 预算足够输出完整 JSON；
  3. 验证硅基流动对 `enable_thinking=false` 的参数是否对该模型生效，必要时换 API 参数或模型；
  4. 端到端验证 `POST /api/chat/query` 返回 200 且 `assistant_message.rich_blocks` 含引用与风险提示。

### 问题 2（已修复）：pytest 未隔离 .env

- **标准**：technicalChecks #3
- **状态**：**已修复** — `test_health.py` 现接受 `mocked` 或 `ready`，并校验双 LLM 字段名

### 问题 3（已修复）：前端 chat/query 超时过短

- **标准**：浏览器路径
- **状态**：**已修复** — `chat.ts` 使用 `timeout: 120000`；本轮 Playwright 等待 91s 未触发 10s 超时

## 真实联调证据（第 3 轮）

```text
# 模型配置（值不写报告）
LLM_INTENT_MODEL=Qwen/Qwen3.5-9B
LLM_MODEL=Qwen/Qwen3.5-27B
LLM_INTENT_API_KEY / LLM_API_KEY: 均已配置

$ curl http://127.0.0.1:18199/api/config/status
→ 意图识别 ready, 主输出 ready, missing_fields=[]

$ curl -X POST .../api/chat/query
→ HTTP 502, message="LLM 返回内容无法解析为 JSON" (~22s)
→ 服务端日志: reasoning_content 以 "Thinking Process:" 开头，非 JSON

$ REAL_API_TEST=1 pytest test_real_siliconflow_llm_call
→ FAILED: LLMClientError: LLM 返回内容无法解析为 JSON

# Playwright 设置页双视口: PASS (LLM_INTENT_*, LLM_*, ready, 无 sk-)
# Playwright 客户端问答: POST /api/chat/query status=502, title=新对话, 无助手消息
```

## 与第 2 轮对比

| 项目 | 第 2 轮 | 第 3 轮 |
|------|---------|---------|
| pytest | 16 passed, 1 failed | **20 passed, 1 skipped** |
| config status | 双 LLM ready | **双 LLM ready（含独立意图 Key）** |
| 失败点 | content 为空 | **reasoning_content 为思考文本，JSON 解析失败** |
| 前端超时 | 10s 导致浏览器失败 | **已修复（120s）** |
| REAL_API_TEST | content 为空 | **JSON 解析失败** |
| chat/query | 502 | **502（不同根因）** |

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | 端口 8099 被其他项目（`auto-cs` / `app.main:app`）占用 | 环境 | 验收前释放端口或文档化切换流程 |
| 2 | `trace_service.py` 仍保留 `create_fallback_trace` 历史方法 | Trace | 后续清理任务 |

## 系统级经验

- **类型**：重复
- **问题摘要**：Qwen3.5 系列在 `enable_thinking=false` 下仍可能将非 JSON 思考过程写入 `reasoning_content`；仅回退读取 `reasoning_content` 不足以完成 JSON 结构化任务。
- **影响范围**：所有使用硅基流动 OpenAI 兼容 API 且选用 Qwen3/Qwen3.5 推理模型的 Web 项目
- **建议规则**：意图识别/质检等 JSON 模式调用应默认使用非推理模型；若必须用推理模型，`_parse_json_payload` 需能从 reasoning 文本中提取末尾 JSON 块并做 finish_reason=length 防护；`REAL_API_TEST=1` 应覆盖完整 `recognize_intent` 路径。
