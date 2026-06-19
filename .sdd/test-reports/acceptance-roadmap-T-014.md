# 用户验收清单：T-014 Query 改写节点（F18）Phase ①

**前置**：后端 `8099`、前端 `5199`，`VITE_USE_MOCK=false`，`LANGGRAPH_ENV=local`  
**依赖**：T-015 短期记忆 ✅、T-016 pending_slots ✅、T-017 多轮上下文注入 ✅

> **目标**：多轮续问「它一季报怎么样」时，RAG 使用规则拼接后的 `retrieval_query` 检索；显性完整问句不被退化；Trace 可见改写前后对比。

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

## 1. 多轮续问改写（AC1 主路径）

在同一**新会话**中连续提问：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 1 | 宁德时代基本面怎么样 | 正常个股分析回答 | |
| 2 | 它一季报怎么样 | 延续宁德时代语境的一季报分析；正文点明标的与报告期 | |

**Trace 检查（第 2 轮）**：

| # | 步骤 | 验收点 | 期望 | 通过 □ |
|---|------|--------|------|--------|
| 1.1 | `query_rewrite` | `input.normalized_query` | `它一季报怎么样`（或等价归一化） | |
| 1.2 | `query_rewrite` | `output.retrieval_query` | 含「宁德时代」与「一季报」等检索友好拼接 | |
| 1.3 | `query_rewrite` | `output.rewrite_method` | `rule_multiturn` 或 `rule_slots`（非 passthrough） | |
| 1.4 | `query_rewrite` | `output.retrieval_query_changed` | `true` | |
| 1.5 | `rag_retrieval` | `input.retrieval_query` | 与 `query_rewrite` 输出一致 | |
| 1.6 | `rag_retrieval` | `input.query`（实际检索句） | 使用改写后语句，**不是**仅「它一季报怎么样」 | |
| 1.7 | `rag_retrieval` | 命中片段 | 与宁德时代相关 | |

---

## 2. 显性问句不退化（AC2）

在新会话中**单轮**提问：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 1 | 罗莱生活 2026 年一季报 | 正常回答；检索不因改写而缩短问句 | |

**Trace 检查**：

| # | 步骤 | 验收点 | 期望 | 通过 □ |
|---|------|--------|------|--------|
| 2.1 | `query_rewrite` | `output.rewrite_method` | `passthrough` | |
| 2.2 | `query_rewrite` | `output.retrieval_query` | 与 `normalized_query` 一致（含公司名与期别） | |
| 2.3 | `query_rewrite` | `output.retrieval_query_changed` | `false` | |
| 2.4 | `rag_retrieval` | `input.query` | 保持完整显性问句 | |

---

## 3. 澄清链路不经过改写（回归）

在新会话中**直接**提问（无标的）：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 1 | 一季报怎么样 | 触发澄清；Trace **不出现** `query_rewrite` 步骤 | |

---

## 4. Embedding 降级不阻断（AC3，可选）

若本地 Embedding 未配置或不可用：

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 4.1 | 任意问股路径 | 仍能返回回答（BM25-only 或 mock 降级） | |
| 4.2 | `rag_retrieval` Trace | `output.mode` 可为 `bm25` / `mock`，流程不中断 | |
| 4.3 | `query_rewrite` | 仍正常产出 `retrieval_query`（与 embedding 无关） | |

---

## 5. supplement_mode 未误改（回归）

本项需 evidence gap 补检索路径触发（若当前环境不易触发，可跳过并注明）：

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 5.1 | `rag_retrieval`（supplement_mode） | 使用 `supplement_rag_queries`，**不**用主路径 `retrieval_query` 替代 planner 产出 | |

---

**通过后请回复**：「T-014 Query 改写验收通过」或指出未通过条目编号。

**用户门禁端口说明**：本清单默认 Agent 自动验证端口（后端 `8099`、前端 `5199`）。若需与本地其他实例隔离，可临时设置 `VITE_BACKEND_PROXY_TARGET=http://localhost:8003` 并将后端改监听 `8003`、前端 `5175`。
