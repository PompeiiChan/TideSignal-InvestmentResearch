# 用户验收清单：T-015 五轮短期记忆窗口（F20）

**前置**：后端 `8099`、前端 `5199`，`VITE_USE_MOCK=false`，`LANGGRAPH_ENV=local`

---

## 0. 启动服务

**终端 1 — 后端**

```bash
cd Projects_Repo/smart-investment-research/backend
PYTHONPATH=.. ../.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8099
```

**终端 2 — 前端**

```bash
cd Projects_Repo/smart-investment-research/frontend
VITE_USE_MOCK=false npm run dev -- --host 127.0.0.1 --port 5199
```

浏览器打开：`http://127.0.0.1:5199`

---

## 1. 续问对话（意图层）

在同一新会话中连续提问：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 1 | 宁德时代基本面怎么样 | 正常个股分析回答 | |
| 2 | 一季报呢 | 延续宁德时代语境（非「请提供公司名称」）；意图应为问股/个股分析 | |

**Trace 检查（P04 管理端）**：打开本轮 Trace → `intent_recognition` 步骤 JSON：

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 1.1 | `input.history_summary` | 非空，含上轮「宁德时代」摘要 | |
| 1.2 | `input.normalized_query` | `一季报呢` | |
| 1.3 | `output.intent_id` | `stock_analysis`（或延续上轮主意图） | |

---

## 2. 六轮窗口截断（上下文层）

在同一会话继续追问至 **第 6 轮**（含首轮共 6 次 user 提问），例如依次问：

1. 宁德时代基本面怎么样  
2. 一季报呢  
3. 估值呢  
4. 主要风险有哪些  
5. 和比亚迪比怎么样  
6. 毛利率趋势呢  

打开 **第 6 轮** Trace → `context_preprocess` 步骤：

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 2.1 | `input.history_count` | `10`（最近 5 轮 prior QA） | |
| 2.2 | `input.history_truncated` | `true` | |
| 2.3 | `input.history_window_rounds` | `5` | |
| 2.4 | `output.history_summary` | 仅含最近 5 轮对话摘要，**不含**第 1 轮最早一问一答 | |
| 2.5 | `output.context_pack.history_count` | 与 `input.history_count` 一致 | |

> UI 会话列表仍可展示全部历史消息；截断仅影响注入 Agent 的 `chat_history` / `history_summary`。

---

## 3. 配置一致性（可选抽检）

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 3.1 | `backend/config/app.toml` | `short_term_qa_rounds = 5` | |
| 3.2 | 环境变量（若设置） | `SHORT_TERM_QA_ROUNDS=5` 与行为一致 | |

---

## 4. 回归确认

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 4.1 | 首轮单轮问股 | 与 T-013 行为一致，无退化 | |
| 4.2 | Trace 时间线 | `context_preprocess` → `intent_recognition` 等节点正常展示 | |

---

**通过后请回复**：「T-015 短期记忆验收通过」或指出未通过条目编号。

**用户门禁端口说明**：本清单使用 Agent 自动验证端口（后端 `8099`、前端 `5199`）。若需与本地其他实例隔离，可临时设置 `VITE_BACKEND_PROXY_TARGET=http://localhost:8003` 并将后端改监听 `8003`、前端 `5175`。
