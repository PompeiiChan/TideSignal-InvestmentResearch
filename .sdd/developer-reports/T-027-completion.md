# T-027 完成报告：问股 citation 区瘦身

> **任务 ID**：T-027  
> **完成时间**：2026-06-20

## 变更摘要

1. **新建** `backend/src/services/citation_context_compact.py`：财务/估值/API/RAG slim 与 compact JSON dump。
2. **`format_citation_context`** 增加 `compact` 参数；compact 时省略重复时间块、截断 RAG snippet、瘦身工具 JSON。
3. **`profile.use_compact_citation_context`**：`stock_full` / `stock_narrative` / `compound` 启用 compact。
4. **`response_assembly`** 按 profile 传 `compact`，Trace 写入 `citation_context_mode`。
5. **单测** `test_citation_context_compact.py`（6 条）。

## 压缩策略

| 区域 | compact 行为 |
|------|-------------|
| 系统时间块 | 省略（system prompt 已有） |
| 多期财务 JSON | 保留关键字段，无 indent |
| 估值历史 | 分位摘要 + 最近 4 季 quarterly_series |
| API facts | 最多 6 条，字段裁剪 |
| 研报元数据 | 最多 3 条，字段裁剪 |
| RAG snippet | 最多 6 hit，每段 ≤480 字符 |

## 合成 payload 对比（单测）

`test_compact_reduces_char_count_for_stock_payload`：compact 字符数 < full × 0.7（降 ≥30%）。

## 已知限制

- hotspot/data profile 仍用 full 模式（体量较小，未启用 compact）。

## 用户门禁（2026-06-20）

- 问股 live 联调：**吐首字速度明显变快**（与 citation 区 prefill 缩短一致）。
- 经验已沉淀至 `.sdd/experience.md` [T-027]。
