# 测试报告：T-014 Query 改写节点（F18）Phase ①

**测试时间**：2026-06-20  
**Tester Agent ID**：cursor-tester

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 多轮场景「它一季报怎么样」在上一轮已明确 stock_name 时，RAG 使用改写后的 retrieval_query 且 Trace 可见改写前后对比 | **PASS** | `build_retrieval_query` 续问拼接含「宁德时代」「一季报」（`test_multiturn_followup_with_stock_name`）；`query_rewrite` 节点 Trace 含 `input.normalized_query` / `output.retrieval_query`（`test_query_rewrite_node_outputs_retrieval_query`）；`rag_retrieval` 主路径 `retrieve` 收到 `retrieval_query` 而非「一季报呢」（`test_rag_retrieval_uses_retrieval_query_for_main_path`） |
| 2 | 显性提问（如「罗莱生活 2026 年一季报」）改写后语义不退化，混合检索命中数不低于改写前 | **PASS** | `_query_already_rich` → `passthrough`，`retrieval_query == normalized_query`、`changed=False`（`test_explicit_query_passthrough`、`test_query_rewrite_node_passthrough_for_rich_query`）；主路径仍用原句检索，不人为缩短 Query |
| 3 | Embedding 不可用时，改写逻辑不阻断 BM25-only 降级路径 | **PASS** | 改写纯字符串构建，无 embedding 依赖（`retrieval_query.py` 无 RagService/LLM 调用）；`test_rag_retrieval_uses_retrieval_query_for_main_path` mock `embedding_connected=False` 仍完成 retrieve；`rag_retrieval` 沿用既有 BM25-only 降级 |

## technicalChecks

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | `docs/agent/langgraph-flow.md` 节点清单与流转图已包含 `query_rewrite` | **PASS** | 节点表 L20；Mermaid L49-50 `clarification_check → query_rewrite → routing_decision`；§7.1 状态「已实现 Phase ①」；Trace 映射 L136 |
| 2 | `rag_retrieval` 优先使用 `state.retrieval_query`，缺省回退 `normalized_query` | **PASS** | `rag_retrieval.py:98-99` `retrieval_query or normalized_query` → `effective_query`；主路径 `retrieve`/`retrieve_stock_narrative` 等均用 `effective_query` |
| 3 | pytest 含 `query_rewrite` / `build_retrieval_query` 单测 | **PASS** | `test_retrieval_query.py`（5）、`test_query_rewrite_node.py`（2）、`test_rag_retrieval_query.py`（2）、图回归 `test_stock_path_trace_contains_rag_and_tool` 含 `query_rewrite` |

## 代码审查要点

| 要点 | 结果 | 位置 |
|------|------|------|
| 图结构 clarification → query_rewrite → routing_decision | **PASS** | `graph.py:65-74`；`routing.py:19-25` `route_after_clarification` → `query_rewrite` |
| 澄清链路不经过改写 | **PASS** | `need_clarification` → `clarification_response` → END（`graph.py:69-73`） |
| `query_rewrite` 节点注册 | **PASS** | `__init__.py:16,30,61` |
| state 字段增补 | **PASS** | `state.py:55-57` `retrieval_query`、`rewrite_method`、`retrieval_query_changed` |
| supplement_mode 未误改 | **PASS** | `rag_retrieval.py:135-167` supplement 仍用 `supplement_rag_queries`；`test_rag_retrieval_supplement_mode_ignores_retrieval_query` |
| 密钥泄露 | **PASS** | 变更文件无真实 API Key / Token |
| TODO/FIXME | **PASS** | T-014 变更文件无遗留标记 |
| httpx trust_env | **N/A** | 本任务无新增 HTTP 客户端 |

## 命令执行摘要

### pytest（项目根，Tester 独立执行）

```bash
cd Projects_Repo/smart-investment-research
PYTHONPATH=. .venv/bin/python -m pytest \
  backend/tests/test_retrieval_query.py \
  backend/tests/test_query_rewrite_node.py \
  backend/tests/test_rag_retrieval_query.py \
  backend/tests/test_langgraph_execution.py -v --tb=short
```

```text
T-014 相关：9/9 passed
  test_retrieval_query.py          5 passed
  test_query_rewrite_node.py       2 passed
  test_rag_retrieval_query.py      2 passed
  test_stock_path_trace_contains_rag_and_tool  PASSED（含 query_rewrite 节点）

同文件其他用例：test_tool_call_node_invokes_market_ranking_tool FAILED
  ModuleNotFoundError: No module named 'src'（patch 路径问题，与 T-014 无关）
总计：23 passed, 1 failed
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
| 1 | `test_tool_call_node_invokes_market_ranking_tool` 因 `patch('src...')` 模块路径失败 | `test_langgraph_execution.py` | 修复 patch 目标为 `backend.src...` 或等价路径；非 T-014 blocker |
| 2 | AC2「命中数不低于改写前」未做真实混合检索 A/B 对比 | 检索质量 | Phase ① 以 passthrough 保证显性问句不退化；端到端召回对比可放用户门禁或后续 Phase |
| 3 | AC1 端到端续问效果仍依赖 LLM 与知识库内容 | 用户门禁 | 技术验收以规则改写 + RAG 入参为准；见 `acceptance-roadmap-T-014.md` |

## 用户门禁

本任务 `user_gate: true`。技术验收 **PASS**；用户按 `.sdd/test-reports/acceptance-roadmap-T-014.md` 完成 live 验证后回复确认。
