# 用户验收清单：T-014-P2 Query 改写 passthrough + 维度多 Query

**前置**：后端 `8099`、前端 `5199`，`VITE_USE_MOCK=false`，`LANGGRAPH_ENV=local`  
**依赖**：T-014 Phase ① ✅、T-015 短期记忆 ✅、T-016 pending_slots ✅、T-017 多轮上下文 ✅

> **目标**：修复 BC-009「海天味业基本面」被收成「海天味业 财报」；宽维度问股多路检索；续问与显性问句行为不退化。

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

> 用户门禁端口：后端 `8003`、前端 `5175`，设置 `VITE_BACKEND_PROXY_TARGET=http://localhost:8003`。

---

## 1. 海天味业基本面 — passthrough + 多路检索（AC1 / BC-009）

在新会话中**单轮**提问：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 1 | 海天味业基本面 | 正常个股基本面分析；正文覆盖财务、盈利、竞争力等宽维度，而非仅财报口径 | |

**Trace 检查**：

| # | 步骤 | 验收点 | 期望 | 通过 □ |
|---|------|--------|------|--------|
| 1.1 | `query_rewrite` | `output.retrieval_query` | **保持原句**「海天味业基本面」，**不是**「海天味业 财报」 | |
| 1.2 | `query_rewrite` | `output.rewrite_method` | `rule_dimension_split` | |
| 1.3 | `query_rewrite` | `output.retrieval_queries` | ≥2 条（含财务/盈利/研报等子 query） | |
| 1.4 | `query_rewrite` | `output.retrieval_query_changed` | `true`（因多路拆分） | |
| 1.5 | `rag_retrieval` | `input.retrieval_query` | 与 1.1 一致（原句） | |
| 1.6 | `rag_retrieval` | `input.retrieval_queries` | 与 1.3 一致 | |
| 1.7 | `rag_retrieval` | 命中片段 | 来源多样（财报/研报/公告等），非单一财报关键词 | |

---

## 2. 续问改写不退化（AC2）

在同一**新会话**中连续提问：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 1 | 宁德时代基本面怎么样 | 正常个股分析 | |
| 2 | 它一季报怎么样 | 延续宁德时代语境的一季报分析 | |

**Trace 检查（第 2 轮）**：

| # | 步骤 | 验收点 | 期望 | 通过 □ |
|---|------|--------|------|--------|
| 2.1 | `query_rewrite` | `output.retrieval_query` | 含「宁德时代」与「一季报」 | |
| 2.2 | `query_rewrite` | `output.rewrite_method` | `rule_multiturn` 或 `rule_slots` | |
| 2.3 | `query_rewrite` | `output.retrieval_queries` | 空或单路（续问不拆多维度） | |
| 2.4 | `rag_retrieval` | `input.query` | 使用改写后语句检索 | |

---

## 3. 显性期别问句 passthrough（AC3）

在新会话中**单轮**提问：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 1 | 罗莱生活 2026 年一季报 | 正常回答；主 query 不被改写缩短 | |

**Trace 检查**：

| # | 步骤 | 验收点 | 期望 | 通过 □ |
|---|------|--------|------|--------|
| 3.1 | `query_rewrite` | `output.rewrite_method` | `passthrough` | |
| 3.2 | `query_rewrite` | `output.retrieval_query` | 与输入一致 | |
| 3.3 | `query_rewrite` | `output.retrieval_queries` | 空（期别显性问句不拆多路） | |
| 3.4 | `query_rewrite` | `output.retrieval_query_changed` | `false` | |

---

## 4. Embedding 降级不阻断（AC4，可选）

若本地 Embedding 未配置或不可用：

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 4.1 | 「海天味业基本面」问股 | 仍能返回回答；`rag_retrieval` `output.mode` 可为 `bm25` / `mock` | |
| 4.2 | 多路检索路径 | 流程不中断；Trace 仍可见 `retrieval_queries` | |
| 4.3 | `query_rewrite` | 正常产出 `retrieval_query` + `retrieval_queries`（与 embedding 无关） | |

---

## 5. supplement_mode 回归（可选）

若当前环境可触发 evidence gap 补检索：

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 5.1 | `rag_retrieval`（supplement_mode） | 仍用 `supplement_rag_queries`，不受 `retrieval_queries` 主路径影响 | |

---

**通过后请回复**：「T-014-P2 Query 改写 passthrough 验收通过」或指出未通过条目编号。

**参考文档**：`docs/agent/response-bad-case.md` BC-009
