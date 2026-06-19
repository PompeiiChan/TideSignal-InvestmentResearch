# 测试报告：T-016 会话 pending_slots 多轮闭环（F19）

**测试时间**：2026-06-19  
**Tester Agent ID**：cursor-tester

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 第一轮问「宁德时代基本面怎么样」并回答后，第二轮问「它 2026 一季报怎么样」时，`slot_extraction` 输出含 `stock_name=宁德时代`（或等价 code），无需用户重复公司名 | **PASS** | `test_slot_extraction_merges_pending_stock_name` mock LLM 仅返回 `time_range`/`analysis_dimension`，state 含 `pending_slots.stock_name=宁德时代`；断言 `result["slots"]["stock_name"]=="宁德时代"`、`stock_name` 在 `inherited_slot_keys`、不在 `missing_slots`。BC-008 等价路径「一季报呢」已覆盖 |
| 2 | 用户在新一轮显式更换标的（如改问「泸州老窖呢」）时，继承槽位被覆盖，不误用上一轮公司 | **PASS** | `test_merge_overrides_stock_name_when_user_switches` 与 `test_slot_extraction_overrides_pending_stock_name` 断言 merged `stock_name=泸州老窖`、`overridden_slot_keys` 含 `stock_name`、不在 `inherited_keys` |
| 3 | 缺必填槽位时仍走 `clarification_response`；已继承槽位不计入 missing | **PASS** | `test_missing_stock_name_still_clarifies` → `need_clarification=true`；`test_inherited_stock_name_skips_clarification` → 继承 `stock_name` 时 `need_clarification=false`；`filter_missing_after_inherit` 单测移除 inherited `stock_name` |

## technicalChecks

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | 槽位必填表与澄清阈值集中配置，节点只引用不硬编码 | **PASS** | `slot_memory.py` 定义 `REQUIRED_SLOTS_BY_INTENT`、`INHERITABLE_SLOTS_BY_INTENT`、`SLOT_CONFIDENCE_CLARIFY_THRESHOLD`；`clarification_check.py` 通过 `REQUIRED_SLOTS_BY_INTENT.get(intent_id)` 引用，无重复硬编码必填表 |
| 2 | Trace 的 slot_extraction / clarification_check 可见继承前后 slots 对比 | **PASS** | `slot_extraction` output 含 `extracted_slots`、`pending_slots`、`slots`/`active_slots`、`inherited_slot_keys`、`overridden_slot_keys`；`clarification_check` input/output 含 `inherited_slot_keys`；`test_slot_extraction_merges_pending_stock_name` 断言 trace `raw_json.output` 字段 |
| 3 | pytest 含多轮槽位继承用例 | **PASS** | 见下方命令输出（10 passed） |

## 代码审查要点

| 要点 | 结果 | 位置 |
|------|------|------|
| merge 续问继承 | **PASS** | `slot_memory.merge_pending_slots`：按 `INHERITABLE_SLOTS_BY_INTENT` 过滤 pending，extracted 非空覆盖 |
| 澄清轮不写 pending | **PASS** | `should_persist_pending(..., need_clarification=True)` → False；`runner.run_stream` 仅 `elif should_persist_pending` 时 `update_context_state`，澄清轮跳过写入、保留上轮 pending |
| 显式覆盖 | **PASS** | `merge_pending_slots` 检测 extracted 与 pending 值不同 → `overridden_keys` |
| Trace 字段 | **PASS** | `slot_extraction.py:91-101`、`clarification_check.py:171-178,222-227` |
| REQUIRED_SLOTS 单一配置源 | **PASS** | 仅 `slot_memory.REQUIRED_SLOTS_BY_INTENT`；`clarification_check._missing_core_slots` 引用 |
| context_state 读写 | **PASS** | `runner.run_stream` 启动注入 pending；成功路由后 `build_context_state_from_run`；`chit_chat` 等 `should_clear_pending` 清空 |
| 密钥泄露 | **PASS** | 变更文件无真实 API Key / Token |
| TODO/FIXME | **PASS** | T-016 变更文件无遗留标记 |

## BC-008 回归

| 路径 | 结果 | 测试 |
|------|------|------|
| 宁德时代 +「一季报呢」续问继承 `stock_name`、不澄清 | **PASS** | `test_slot_extraction_merges_pending_stock_name` + `test_inherited_stock_name_skips_clarification` |
| 「泸州老窖呢」覆盖 pending | **PASS** | `test_slot_extraction_overrides_pending_stock_name` |
| 文档 | **PASS** | `docs/agent/response-bad-case.md` §BC-008 已记录修复与验收要点 |

## 命令执行摘要

### pytest（项目根，Tester 独立执行）

```bash
cd Projects_Repo/smart-investment-research
PYTHONPATH=. .venv/bin/python -m pytest \
  backend/tests/test_slot_memory.py \
  backend/tests/test_slot_extraction_multiturn.py \
  backend/tests/test_clarification_inherited.py -v
```

```text
10 passed in 0.54s
```

### ruff（项目根，Tester 独立执行）

```bash
PYTHONPATH=. .venv/bin/python -m ruff check \
  backend/src/services/slot_memory.py \
  backend/src/agents/nodes/slot_extraction.py \
  backend/src/agents/nodes/clarification_check.py \
  backend/src/integrations/langgraph/runner.py
```

```text
All checks passed!
```

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|-------------|
| 1 | `runner.run_stream` 的 context_state 持久化尚无集成单测（依赖 `should_persist_pending` 单元测试） | 测试覆盖 | 可选补充 mock SessionRepository 用例；非 T-016 blocker |
| 2 | AC1 文案为「它 2026 一季报怎么样」，自动化用例使用 BC-008 等价短续问「一季报呢」 | 用例表述 | 用户门禁 roadmap 含两种表述；行为等价 |

---

**技术验收结论**：T-016 代码与单测满足 acceptanceCriteria 与 technicalChecks。用户门禁见 `.sdd/test-reports/acceptance-roadmap-T-016.md`。
