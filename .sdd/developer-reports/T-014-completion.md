# T-014 Query 改写节点（F18）— 开发完成报告

> **任务 ID**：T-014  
> **阶段**：Phase ① 规则+槽位拼接  
> **完成日期**：2026-06-19  
> **状态**：待 Tester 验收

---

## 1. 实现摘要

新增 LangGraph 节点 `query_rewrite`，在澄清通过后、路由决策前，以纯规则将口语化/多轮指代 Query 拼接为 `retrieval_query`；`rag_retrieval` 主路径优先使用改写结果，Trace 可见改写前后对比。

## 2. 变更文件

| 文件 | 变更 |
|------|------|
| `backend/src/services/retrieval_query.py` | 新增 `build_retrieval_query`（passthrough / rule_slots / rule_multiturn） |
| `backend/src/agents/nodes/query_rewrite.py` | 新增节点，Trace 写入 input/output |
| `backend/src/integrations/langgraph/state.py` | 增补 `retrieval_query`、`rewrite_method`、`retrieval_query_changed` |
| `backend/src/integrations/langgraph/routing.py` | `route_after_clarification` → `query_rewrite` |
| `backend/src/integrations/langgraph/graph.py` | 插入 `query_rewrite` 边 |
| `backend/src/agents/nodes/rag_retrieval.py` | 主路径用 `effective_query`；Trace 含改写前后 |
| `backend/src/agents/nodes/__init__.py` | 注册 `query_rewrite` |
| `docs/agent/langgraph-flow.md` | 节点表、Mermaid、§7.1、Trace 映射更新 |
| `backend/tests/test_retrieval_query.py` | 规则单测 |
| `backend/tests/test_query_rewrite_node.py` | 节点单测 |
| `backend/tests/test_rag_retrieval_query.py` | RAG 使用 retrieval_query 单测 |
| `backend/tests/test_langgraph_preprocessing.py` | 路由与图序列回归 |
| `backend/tests/test_langgraph_execution.py` | 问股路径含 `query_rewrite` |

## 3. 验收映射

| AC | 实现 |
|----|------|
| 多轮「它一季报怎么样」+ stock_name | `rule_multiturn`/`rule_slots` → Trace `normalized_query` / `retrieval_query` 对比 |
| 显性问句「罗莱生活 2026 年一季报」不退化 | `_query_already_rich` → passthrough |
| Embedding 不可用不阻断 | 改写纯字符串；RAG 仍走既有 BM25-only 降级（`embedding_connected=False` 单测覆盖） |

## 4. 测试

```bash
cd Projects_Repo/smart-investment-research
PYTHONPATH=. .venv/bin/python -m pytest \
  backend/tests/test_retrieval_query.py \
  backend/tests/test_query_rewrite_node.py \
  backend/tests/test_rag_retrieval_query.py -q
```

结果：**9 passed**（2026-06-19）

图回归：`test_langgraph_preprocessing`、`test_langgraph_execution::test_stock_path_trace_contains_rag_and_tool` 含 `query_rewrite` 节点。

## 5. 质量门禁

- `ruff check`：通过（改动文件）
- `mypy`：通过（`retrieval_query.py`、`query_rewrite.py`）

## 6. 非目标（未做）

- Phase ② LLM 改写
- Phase ③ 多 Query 扩展 / HyDE
- `supplement_mode` 查询改写
- 前端改造

---

**等待 Orchestrator 调度 Tester 验证。**
