# 测试报告：T-017 多轮上下文注入下游节点（F20）

**测试时间**：2026-06-19  
**Tester Agent ID**：cursor-tester

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 多轮问股场景：第二轮追问在上轮同一标的语境下，`response_assembly` 生成内容延续标的与时间口径，不出现「请提供公司名称」类退化 | **PASS** | `test_response_assembly_injects_multiturn_block` 捕获 user prompt，含 `【多轮对话上下文】`、`宁德时代`、`不得要求用户重复提供公司名称`；`assembly.py` §二点五、`stock_analysis.py` §十三 增加多轮续问约束 |
| 2 | Trace 中 slot_extraction、response_assembly 的 input 含 `history_summary` 或 `active_slots` 字段 | **PASS** | `slot_extraction.py:45-52` input 含 `history_summary`；`response_assembly.py:346-353` input 含 `history_summary`、`active_slots`、`conversation_context`；单测断言 trace input 字段 |
| 3 | 无历史的首轮对话行为与当前单轮一致，不因注入逻辑回归 | **PASS** | `test_build_conversation_context_first_turn_empty`：`history_summary=""` 时 `has_context=false`；`test_response_assembly_skips_multiturn_block_without_history`：首轮 user prompt 不含 `【多轮对话上下文】` |

## technicalChecks

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | 仅注入短期窗口内上下文，不读取超出 5 轮 QA 的消息 | **PASS** | `conversation_context.py` 消费 state 已有 `history_summary`（由 T-015 `SHORT_TERM_QA_ROUNDS=5` 截断），本模块不扩窗、不直接读 DB 历史 |
| 2 | Prompt 更新：slots / stock_analysis / assembly 对多轮续问的约束与 _shared 版式不冲突 | **PASS** | `assembly.py:88-94`、`stock_analysis.py:223-232` 独立章节；`slots.py` 保留既有 pending_slots 段落 |
| 3 | pytest 含 response_assembly 多轮上下文用例 | **PASS** | 见下方命令输出（9 passed，含 2 条 assembly 多轮用例） |

## 代码审查要点

| 要点 | 结果 | 位置 |
|------|------|------|
| 首轮空 context | **PASS** | `conversation_context.py:67-68`：`history` 空或无关键槽位且无 inherited → `has_context=false` |
| 续问注入 carryover | **PASS** | `build_conversation_context` 返回 `carryover_hint`；`format_conversation_context_for_prompt` 输出摘要与槽位行 |
| evidence_pack.conversation_context | **PASS** | `evidence_merge.py:233-234`；`test_evidence_merge_writes_conversation_context` |
| assembly user_prompt 多轮块 | **PASS** | `response_assembly.py:391-397` |
| stock_analysis_agent payload | **PASS** | `stock_analysis_agent.py:41-53`；`test_stock_analysis_agent_passes_conversation_context` |
| RAG entity 过滤（短续问 + stock_name） | **PASS** | `rag_retrieval.py:113-126` trace 含 `active_slots`/`stock_name`；`224-226` 默认 retrieve 路径 `len(query)<=12` 时 `filter_hits_by_entity` |
| 5 轮窗口不扩窗 | **PASS** | `enrich_state_conversation_context` 仅读 state，窗口截断在 T-015 `short_term_memory` / runner |
| 密钥泄露 | **PASS** | 变更文件无真实 API Key / Token |
| TODO/FIXME | **PASS** | T-017 变更文件无遗留标记 |

## 命令执行摘要

### pytest（项目根，Tester 独立执行）

```bash
cd Projects_Repo/smart-investment-research
PYTHONPATH=. .venv/bin/python -m pytest \
  backend/tests/test_conversation_context.py \
  backend/tests/test_response_assembly_multiturn.py \
  backend/tests/test_stock_analysis_agent_multiturn.py \
  backend/tests/test_evidence_merge_context.py \
  backend/tests/test_slot_extraction_multiturn.py -v
```

```text
9 passed in 0.49s
```

### ruff（项目根，Tester 独立执行）

```bash
PYTHONPATH=. .venv/bin/python -m ruff check \
  backend/src/services/conversation_context.py \
  backend/src/agents/nodes/response_assembly.py \
  backend/src/agents/nodes/evidence_merge.py \
  backend/src/agents/nodes/stock_analysis_agent.py
```

```text
response_assembly.py:81-86 E402 Module level import not at top of file（2 errors）
```

> **判定说明**：E402 为 `response_assembly.py` 既有结构（helper 函数定义后再 import `_helpers`/`citation_rules`），非 T-017 引入；`conversation_context.py`、`evidence_merge.py`、`stock_analysis_agent.py` 无 ruff 问题。T-017 `acceptanceCriteria` / `technicalChecks` 未要求 ruff 全绿，不计入 FAIL。

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|-------------|
| 1 | `response_assembly.py` E402 模块级 import 不在文件顶部 | 代码风格 | 可选后续整理 import 顺序；非 T-017 blocker |
| 2 | `rag_retrieval` 短续问 entity 过滤无独立单测 | 测试覆盖 | 逻辑已在 `rag_retrieval.py:225-226` 静态可证；可选补 mock retrieve 用例 |
| 3 | AC1 端到端「不出现请提供公司名称」依赖 LLM 遵从 prompt | 用户门禁 | 技术验收以 prompt 注入与约束为准；用户门禁见 `acceptance-roadmap-T-017.md` |

## 用户门禁

本任务 `user_gate: true`。技术验收 **PASS**；用户按 `.sdd/test-reports/acceptance-roadmap-T-017.md` 完成 live 验证后回复确认。
