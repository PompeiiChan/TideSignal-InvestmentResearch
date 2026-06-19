# 用户验收清单：T-017 多轮上下文注入下游节点（F20）

**前置**：后端 `8099`、前端 `5199`，`VITE_USE_MOCK=false`，`LANGGRAPH_ENV=local`  
**依赖**：T-015 短期记忆 ✅、T-016 pending_slots 继承 ✅

> **目标**：续问「一季报呢」时，下游 `stock_analysis_agent` / `response_assembly` / RAG 能利用 `history_summary` + `active_slots`，回答延续标的与时间口径。

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

> 若本地已有其他实例占用端口，可临时使用用户门禁端口：后端 `8003`、前端 `5175`，并设置 `VITE_BACKEND_PROXY_TARGET=http://localhost:8003`。

---

## 1. 续问延续标的与时间口径（AC1 主路径）

在同一**新会话**中连续提问：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 1 | 宁德时代基本面怎么样 | 正常个股分析回答 | |
| 2 | 一季报呢 | **延续宁德时代语境**的一季报分析；正文点明标的与报告期；**不得**出现「请提供公司名称/股票名称」类退化 | |

**可选等价续问**：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 2′ | 估值呢 | 仍围绕宁德时代作答，不要求重复公司名 | |

---

## 2. 首轮无回归（AC3）

在新会话中**仅一轮**提问：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 1 | 宁德时代基本面怎么样 | 与 T-013 单轮行为一致；回答正常，无异常多轮提示残留 | |

---

## 3. Trace 检查（P04 管理端）

打开 **第 2 轮「一季报呢」** 的 Trace：

### 3.1 `slot_extraction` 步骤

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 3.1.1 | `input.history_summary` | 非空，含上轮宁德时代对话 | |
| 3.1.2 | `output.active_slots` | 含 `stock_name=宁德时代` | |
| 3.1.3 | `output.conversation_context.has_context` | `true` | |
| 3.1.4 | `output.conversation_context_preview` | 含 `has_context`、`active_slot_keys` | |

### 3.2 `stock_analysis_agent` 步骤（若路由命中）

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 3.2.1 | `input.history_summary` | 非空 | |
| 3.2.2 | `input.active_slots.stock_name` | `宁德时代` | |
| 3.2.3 | `input.conversation_context.has_context` | `true` | |

### 3.3 `evidence_merge` 步骤

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 3.3.1 | `input.has_conversation_context` | `true` | |
| 3.3.2 | `output.evidence_pack.conversation_context` | `has_context=true`，含 `active_slots` | |

### 3.4 `response_assembly` 步骤

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 3.4.1 | `input.history_summary` | 非空 | |
| 3.4.2 | `input.active_slots` | 含 `stock_name` | |
| 3.4.3 | `input.conversation_context.has_context` | `true` | |

### 3.5 `rag_retrieval` 步骤（若存在）

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 3.5.1 | `input.active_slots` | 含继承的 `stock_name` | |
| 3.5.2 | `input.stock_name` | `宁德时代` | |
| 3.5.3 | 命中片段 | 与宁德时代相关（短续问时 entity 过滤生效） | |

---

## 4. 短期记忆窗口回归（technicalCheck）

在**同一长会话**中连续问股 ≥6 轮（每轮不同小问题即可）：

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 4.1 | 第 6 轮 Trace `context_preprocess` | `history_count` 仍反映最近 5 轮 QA 窗口（与 T-015 一致） | |
| 4.2 | 第 6 轮 `history_summary` | 不含最早一轮完整内容 | |

---

## 5. 真缺槽仍澄清（与 T-016 回归）

在新会话中**直接**提问（无上一轮标的）：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 1 | 一季报怎么样 | 触发澄清，追问股票名称；**不得**因多轮注入误当作续问 | |

---

**通过后请回复**：「T-017 多轮上下文验收通过」或指出未通过条目编号。

**用户门禁端口说明**：本清单默认 Agent 自动验证端口（后端 `8099`、前端 `5199`）。若需与本地其他实例隔离，可临时设置 `VITE_BACKEND_PROXY_TARGET=http://localhost:8003` 并将后端改监听 `8003`、前端 `5175`。
