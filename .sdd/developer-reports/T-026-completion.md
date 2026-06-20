# T-026 完成报告：问数自然语言默认可路由

> **任务 ID**：T-026  
> **完成日期**：2026-06-20  
> **Developer**：cursor-developer

---

## 变更摘要

### 新建

- `backend/src/services/data_query_slot_enrich.py` — 规则 enrich（R1～R7）
- `backend/tests/test_data_query_slot_enrich.py` — 10 条单测

### 修改

- `backend/src/agents/nodes/slot_extraction.py` — data_query 路径 enrich + Trace `data_query_slot_enrich`
- `backend/src/agents/nodes/clarification_check.py` — data_query missing 双保险过滤
- `backend/src/services/compound_routing.py` — 复用 `enrich_data_query_slots`
- `backend/tests/test_langgraph_preprocessing.py` — 澄清分支用例
- `docs/agent/response-bad-case.md` — BC-010
- `.sdd/experience.md`

---

## 质量门禁

```text
ruff check（指定文件）→ 通过
pytest test_data_query_slot_enrich + test_langgraph_preprocessing + test_langgraph_execution
→ 61 passed in ~37s
```

---

## 规则覆盖

| 规则 | 示例 query | 填充 |
|------|------------|------|
| R1 | 行业板块热力图 | metric=行业板块热力图 |
| R2/R3 | 今天涨幅前10的行业板块 / 半导体涨幅前五 | metric=涨幅排行 |
| R4 | 今日成交量最大的板块 | metric=成交额排行 |
| R5 | 任意 data_query | time_range=近一交易日 |
| R7 | 行业板块… | market=A股 |

泛问「帮我查一下数据」不填 metric，仍走澄清。

---

**本功能已完成，等待 Tester 验证。**
