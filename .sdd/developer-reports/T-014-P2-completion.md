# T-014-P2 完成报告 — Query 改写规则优化 + 维度多 Query

> **任务 ID**：T-014-P2  
> **完成日期**：2026-06-20  
> **状态**：待 Tester 验收

---

## 实现摘要

### Step A — Phase ① 修补

| 项 | 实现 |
|----|------|
| 显性问句 passthrough | `_query_has_stock_and_dimension`：公司名 + 分析维度 → `retrieval_query` 保持原句 |
| 去掉默认 append「财报」 | `_should_append_financial_keyword` 仅在期别/业绩类关键词时加财报词 |
| 收紧短句判定 | `_needs_follow_up_rewrite`：「海天味业基本面」不再当续问 |
| 续问保留 | 「它一季报怎么样」+ `stock_name` 仍拼公司 + 一季报 |

### Step B — 规则化多 Query

| 项 | 实现 |
|----|------|
| `build_dimension_retrieval_queries` | 基本面/估值/风险/期别映射 2～4 条子 query |
| `RetrievalQueryPlan` | 含 `retrieval_query`、`retrieval_queries`、`rewrite_method`、`changed` |
| `rewrite_method` | 新增 `rule_dimension_split` |
| `query_rewrite` / `state` | 输出 `retrieval_queries` |
| `rag_retrieval` | `retrieval_queries` ≥2 → `retrieve_targeted`；supplement/narrative/hotspot 不变 |

---

## 修改文件

- `backend/src/services/retrieval_query.py`
- `backend/src/agents/nodes/query_rewrite.py`
- `backend/src/agents/nodes/rag_retrieval.py`
- `backend/src/integrations/langgraph/state.py`
- `backend/tests/test_retrieval_query.py`
- `backend/tests/test_rag_retrieval_query.py`
- `backend/tests/test_query_rewrite_node.py`
- `docs/agent/langgraph-flow.md` §7.1
- `docs/agent/response-bad-case.md` BC-009

---

## 测试

```bash
PYTHONPATH=. .venv/bin/python -m pytest \
  backend/tests/test_retrieval_query.py \
  backend/tests/test_rag_retrieval_query.py \
  backend/tests/test_query_rewrite_node.py -q
```

结果：**15 passed**

---

## 验收对照

| # | 标准 | 自测 |
|---|------|------|
| 1 | 「海天味业基本面」`retrieval_query` 非「海天味业 财报」 | PASS |
| 2 | 同上 `retrieval_queries` ≥2，RAG 走 `retrieve_targeted` | PASS |
| 3 | 「它一季报怎么样」续问改写不退化 | PASS |
| 4 | Embedding 不可用不阻断 BM25 | PASS（mock `embedding_connected=False`） |

---

**本功能已完成，等待 Orchestrator 调度 Tester 验证。**
