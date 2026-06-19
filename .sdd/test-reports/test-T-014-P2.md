# 测试报告：T-014-P2 Query 改写规则优化 + 维度多 Query（F18 续）

**测试时间**：2026-06-20  
**Tester Agent ID**：cursor-tester

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 「海天味业基本面」Trace 中 `retrieval_query` 语义不退化为仅财报；`retrieval_queries` 含多路子 query | **PASS** | `test_haitian_fundamentals_passthrough`：`retrieval_query == "海天味业基本面"`，主 query 不含「财报」，`rewrite_method == rule_dimension_split`；`test_haitian_dimension_split`：`len(retrieval_queries) >= 2`，子 query 含财务/研报维度；`test_query_rewrite_node_outputs_dimension_queries`：节点 Trace `output.retrieval_queries` 与 state 一致；`test_rag_retrieval_uses_retrieval_queries_for_dimension_split`：`retrieval_queries` ≥2 时 `retrieve_targeted` 被调用且 Trace `input.retrieval_queries` 可见 |
| 2 | 「它一季报怎么样」多轮续问改写仍有效 | **PASS** | `test_follow_up_still_rewrites` / `test_multiturn_followup_with_stock_name`：续问拼接含「宁德时代」「一季报」，`changed=True`；`test_query_rewrite_node_outputs_retrieval_query`：节点输出 `retrieval_query` 含公司+期别，`retrieval_queries == []`（单路续问不改多 query） |
| 3 | 显性问句「罗莱生活 2026 年一季报」保持 passthrough | **PASS** | `test_luolai_explicit_passthrough` / `test_explicit_query_passthrough`：`retrieval_query == normalized_query`，`rewrite_method == passthrough`，`changed=False`，`retrieval_queries == []`；`test_query_rewrite_node_passthrough_for_rich_query` 节点层一致 |
| 4 | Embedding 不可用时多 query 检索不阻断 BM25 降级 | **PASS** | `retrieval_query.py` 纯规则字符串构建，无 embedding/RagService 依赖；`test_rag_retrieval_uses_retrieval_queries_for_dimension_split` mock `embedding_connected=False` 仍完成 `retrieve_targeted`；`test_rag_retrieval_uses_retrieval_query_for_main_path` 单路路径同样 `embedding_connected=False` 不阻断 |

## technicalChecks

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | `build_retrieval_query` / `build_dimension_retrieval_queries` 单测覆盖 BC-009 | **PASS** | `test_haitian_fundamentals_passthrough`、`test_haitian_dimension_split`；`docs/agent/response-bad-case.md` BC-009 已记录现象/归因/修复/回归要点 |
| 2 | `rag_retrieval` 在 `retrieval_queries>=2` 时调用 `retrieve_targeted` | **PASS** | `rag_retrieval.py:236-241` 主路径 `else` 分支；`test_rag_retrieval_uses_retrieval_queries_for_dimension_split` |
| 3 | pytest 指定用例集 | **PASS** | 15/15 passed（见命令摘要） |

## 代码审查要点

| 要点 | 结果 | 位置 |
|------|------|------|
| 显性问句 passthrough（公司名+维度） | **PASS** | `retrieval_query.py:66-70` `_query_has_stock_and_dimension`；`227-239` 主决策 |
| 去掉无条件 append「财报」 | **PASS** | `retrieval_query.py:119-130` `_should_append_financial_keyword` 仅期别/业绩类触发；`189-195` 条件 append |
| 收紧短句判定（基本面不算续问） | **PASS** | `retrieval_query.py:73-79` `_needs_follow_up_rewrite` 先排除 `_query_has_stock_and_dimension` |
| 维度多 query 映射 2～4 条 | **PASS** | `retrieval_query.py:133-168` `build_dimension_retrieval_queries`；`MAX_DIMENSION_QUERIES=4` |
| `query_rewrite` 输出 `retrieval_queries` | **PASS** | `query_rewrite.py:48`；`state.py:56` |
| `rag_retrieval` 主路径多路合并 | **PASS** | `rag_retrieval.py:120-128` input_data；`236-245` 分支逻辑 |
| supplement/narrative/hotspot 路径未误改 | **PASS** | `test_rag_retrieval_supplement_mode_ignores_retrieval_query`；`rag_retrieval.py:140-234` 优先分支不变 |
| `langgraph-flow.md` §7.1 已更新 P2 行为 | **PASS** | 节点表 L20/L27；§7.1 L260-265 `retrieval_queries`、`rule_dimension_split` |
| 密钥泄露 | **PASS** | 变更文件无真实 API Key / Token |
| TODO/FIXME | **PASS** | 变更文件无遗留标记 |
| httpx trust_env | **N/A** | 本任务无新增 HTTP 客户端 |

## 命令执行摘要

### pytest（项目根，Tester 独立执行）

```bash
cd Projects_Repo/smart-investment-research
PYTHONPATH=. .venv/bin/python -m pytest \
  backend/tests/test_retrieval_query.py \
  backend/tests/test_rag_retrieval_query.py \
  backend/tests/test_query_rewrite_node.py -v
```

```text
15 passed in 0.37s
```

### ruff（项目根，Tester 独立执行）

```bash
PYTHONPATH=. .venv/bin/python -m ruff check \
  backend/src/services/retrieval_query.py \
  backend/src/agents/nodes/query_rewrite.py \
  backend/src/agents/nodes/rag_retrieval.py
```

```text
All checks passed!
```

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|-------------|
| 1 | AC1 未做真实 KB 端到端召回质量对比（仅验证 Trace 字段与多路调用） | RAG 质量 | 用户门禁清单覆盖 Trace 目视验收；召回提升可后续量化 |
