# T-026 问数自然语言默认可路由（metric / time_range 规则 enrich）— 技术方案

> **任务 ID**：T-026  
> **source_feature**：F19 槽位闭环 / F01 对话体验  
> **依据**：T-025 验收超出范围发现 #1、`docs/agent/response-bad-case.md`（拟 BC-010）  
> **前置**：T-016 ✅、T-025 ✅  
> **产出日期**：2026-06-20  
> **状态**：待 Developer 执行

---

## 1. 背景与问题

T-025 性能优化后，问数/热力图类自然语言在 **live 链路** 上常于 `clarification_check` 提前结束：

| 用户原话（AC 示例） | 现象 | 根因 |
|---------------------|------|------|
| 「今天涨幅前 10 的行业板块」 | 追问 metric，未进入 `response_assembly` | `data_query` 必填 `metric`，LLM 槽位抽取未填 |
| 「行业板块热力图」 | 同上或缺 time_range | 规则 enrich 未覆盖纯热力图 query |
| 「半导体涨幅前五」 | 偶发澄清 | 有 `industry` 无 `metric` |

**已有但未复用**：

- `compound_routing.enrich_slots_for_compound()` 仅复合路由阶段对 `metric=涨幅排行` + `time_range=近一交易日` 做 enrich
- `tool_call.py` 有 `tool_params.setdefault("metric", "涨幅排行")`，但 **澄清发生在 tool_call 之前**
- `heatmap_intent.wants_sector_heatmap()` 已在 assembly 层使用，**slot/clarification 层未用**

**本任务目标**：在 `slot_extraction` 之后、`clarification_check` 之前（或 check 内 normalize），对 `data_query` 意图做 **确定性规则 enrich**，使常见问数/热力图/排行 query **无需澄清即可路由**。

**非目标**：

- 不改 LLM 槽位 Prompt 主逻辑（仅补充规则层）
- 不做 T-025 Phase 3 citation 区瘦身（另立 T-027）
- 不扩展新 Tool（T-020-P2 指数/历史区间 backlog）

---

## 2. 技术方案

### 2.1 新建 `backend/src/services/data_query_slot_enrich.py`

集中规则函数：

```python
def enrich_data_query_slots(query: str, slots: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return (enriched_slots, applied_keys)."""
```

**规则表（按优先级）**：

| 规则 ID | 触发（regex / 函数） | 填充 slot | 值 |
|---------|----------------------|-----------|-----|
| R1 | `wants_sector_heatmap(query)` | `metric` | `行业板块热力图` |
| R2 | `涨幅\|涨跌\|排行\|前\d+\|Top` + `板块\|行业` | `metric` | `涨幅排行` |
| R3 | `涨幅\|涨跌\|排行\|前\d+`（无行业名） | `metric` | `涨幅排行` |
| R4 | `成交额\|成交量\|换手\|量能` | `metric` | `成交额排行`（或现有 tool 约定值） |
| R5 | 任意 data_query 且 `time_range` 空 | `time_range` | `近一交易日` |
| R6 | query 含 `今天\|今日\|最新` 且 time_range 空 | `time_range` | `近一交易日` |
| R7 | `行业板块\|板块涨幅` 且 `market` 空 | `market` | `A股` |

**约束**：

- 仅 **填充空槽位**，不覆盖 LLM 已抽取值
- 与 `compound_routing.enrich_slots_for_compound` 对齐 metric 枚举（读 `data_query_tool_plan` / `market_ranking_lookup` 现有约定）
- 返回 `applied_keys` 供 Trace

### 2.2 接入点

**首选**：`slot_extraction` 节点 `_execute` 末尾，在 `merge_pending_slots` 之后：

```python
if intent_id == "data_query":
    slots, applied = enrich_data_query_slots(normalized_query, slots)
    state trace input: slot_enrich_applied=applied
```

**备选/补充**：`clarification_check._normalize_slot_lists_for_clarification` 对 `data_query`：

- 若 `enrich_data_query_slots` 后 `metric` 已齐，从 `missing_slots` 剔除 `metric`
- 若 `time_range` 已 enrich 为默认值，从 `missing_slots` 剔除 `time_range`（与 `_DEFAULTABLE_SLOTS` 一致，可扩展）

与 T-016 `filter_missing_after_inherit` 顺序：**inherit → enrich → filter missing**。

### 2.3 Trace

`slot_extraction` step output 增加：

```json
{
  "data_query_slot_enrich": {
    "applied_keys": ["metric", "time_range"],
    "metric": "涨幅排行",
    "time_range": "近一交易日"
  }
}
```

`clarification_check` input 保留 enrich 后 slots。

### 2.4 Bad Case 文档

在 `docs/agent/response-bad-case.md` 追加 **BC-010 问数排行/热力图误澄清**，关联 T-026 修复与回归 query 列表。

---

## 3. 验收标准

### 3.1 用户可见（acceptanceCriteria）

| AC | Query | 通过条件 |
|----|-------|----------|
| 1 | 「今天涨幅前 10 的行业板块」 | `need_clarification=false` → 进入 `data_query_agent` → `response_assembly`；含 ranking_table |
| 2 | 「行业板块热力图」 | 不澄清 metric；进入热力图 tool + assembly（template 或 lite） |
| 3 | 「半导体涨幅前五」 | 不澄清；`slots.metric` 有值；排行或澄清仅当 industry 真歧义 |
| 4 | 真缺 metric 的泛问「帮我查一下数据」 | **仍应澄清**（规则不过度兜底） |
| 5 | Trace | `slot_extraction` 可见 `data_query_slot_enrich.applied_keys` |

### 3.2 技术（technicalChecks）

```text
$PY -m ruff check backend/src/services/data_query_slot_enrich.py \
  backend/src/agents/nodes/slot_extraction.py \
  backend/src/agents/nodes/clarification_check.py \
  backend/tests/test_data_query_slot_enrich.py \
  backend/tests/test_langgraph_preprocessing.py -q 通过

$PY -m pytest backend/tests/test_data_query_slot_enrich.py \
  backend/tests/test_langgraph_preprocessing.py \
  backend/tests/test_langgraph_execution.py -q 通过

单测须覆盖 R1～R7 各至少 1 例 + 不覆盖已有 slot 1 例

VITE_USE_MOCK=false：POST /api/chat/query/stream AC1、AC2 各 1 条全链路完成
```

---

## 4. 实施步骤

| 步骤 | 内容 |
|------|------|
| S1 | `data_query_slot_enrich.py` + 单元测试 |
| S2 | 接入 `slot_extraction.py` |
| S3 | `clarification_check` 对 data_query missing  normalize（可选与 S2 二选一，推荐双保险） |
| S4 | langgraph 集成测 / preprocessing 测更新 |
| S5 | BC-010 文档 + `.sdd/experience.md` |
| S6 | 真实 stream 冒烟 AC1/AC2 |

---

## 5. 风险

| 风险 | 缓解 |
|------|------|
| 规则过宽，泛问误填 metric | R3/R4 需关键词；保留「帮我查数据」无匹配 → 仍澄清 |
| 与 compound enrich 重复 | 抽取共享常量到 `data_query_slot_enrich`；compound 可 re-export |
| metric 枚举与 tool 不一致 | 对照 `data_query_tool_plan.py` / `market_ranking_lookup` 参数 |

---

## 6. 文件清单

**新建**

- `backend/src/services/data_query_slot_enrich.py`
- `backend/tests/test_data_query_slot_enrich.py`

**修改**

- `backend/src/agents/nodes/slot_extraction.py`
- `backend/src/agents/nodes/clarification_check.py`（可选 normalize）
- `backend/tests/test_langgraph_preprocessing.py`
- `docs/agent/response-bad-case.md`（BC-010）
- `.sdd/experience.md`

**不改**

- `response_assembly` / assembly 模块
- 前端

---

## 7. 后续 backlog（本任务不做）

| ID | 方向 | 说明 |
|----|------|------|
| **T-027** | assembly P3 | `stock_full` citation 区瘦身（T-025 后 user_chars≈24k） |
| **T-019 收尾** | KB 扩容 | 数据已入库 50 家，补 Tester 报告 + 用户门禁 |
| **T-020-P2** | 问数工具 | 指数/单股报价/历史区间（tool-richness-roadmap） |
| **T-021-P2** | 估值工具 | 同行对比（tool-richness-roadmap） |

---

## 8. 是否可立即开发

**是。** 范围小、无新外部依赖、与 T-025 正交。建议 S1→S2→S4→S6。
