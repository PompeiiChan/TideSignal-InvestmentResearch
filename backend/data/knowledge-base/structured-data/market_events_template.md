# 结构化数据：market_events_template

> 迁移说明：本文由现有知识库资料转换为 Markdown，用于智能投研 demo、RAG 检索、结构化证据追溯和评测。本文不构成投资建议。

## 迁移元数据

| 字段 | 内容 |
|---|---|
| 资料类型 | structured_csv |
| 原始路径 | data/metadata/market_events_template.csv |
| 迁移后目录 | structured-data |
| 迁移文件 | market_events_template.md |

## 数据表说明

- 原始路径：`data/metadata/market_events_template.csv`
- 字段数量：10
- 数据行数：0
- mock 标记统计：`is_mock=true` 0 行，`is_mock=false` 0 行。
- 使用约束：`is_mock=true` 的行仅用于 demo 链路演示或字段补齐，不得作为真实行情、财务或估值事实直接对用户表述。

## 字段

| 序号 | 字段名 |
|---:|---|
| 1 | `event_id` |
| 2 | `event_date` |
| 3 | `title` |
| 4 | `theme` |
| 5 | `summary` |
| 6 | `affected_industries` |
| 7 | `affected_companies` |
| 8 | `sources` |
| 9 | `is_mock` |
| 10 | `notes` |

## 数据

当前 CSV 仅包含表头，暂无数据行。

---
免责声明：本文仅用于智能投研系统知识库迁移与测试，不构成投资建议。投资有风险，入市需谨慎。
