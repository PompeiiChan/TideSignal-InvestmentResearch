# 结构化数据：financial_metrics_template

> 迁移说明：本文由现有知识库资料转换为 Markdown，用于智能投研 demo、RAG 检索、结构化证据追溯和评测。本文不构成投资建议。

## 迁移元数据

| 字段 | 内容 |
|---|---|
| 资料类型 | structured_csv |
| 原始路径 | data/metadata/financial_metrics_template.csv |
| 迁移后目录 | structured-data |
| 迁移文件 | financial_metrics_template.md |

## 数据表说明

- 原始路径：`data/metadata/financial_metrics_template.csv`
- 字段数量：14
- 数据行数：0
- mock 标记统计：`is_mock=true` 0 行，`is_mock=false` 0 行。
- 使用约束：`is_mock=true` 的行仅用于 demo 链路演示或字段补齐，不得作为真实行情、财务或估值事实直接对用户表述。

## 字段

| 序号 | 字段名 |
|---:|---|
| 1 | `company_id` |
| 2 | `period` |
| 3 | `report_type` |
| 4 | `revenue` |
| 5 | `net_profit` |
| 6 | `gross_margin` |
| 7 | `roe` |
| 8 | `operating_cash_flow` |
| 9 | `eps` |
| 10 | `debt_ratio` |
| 11 | `currency` |
| 12 | `source` |
| 13 | `is_mock` |
| 14 | `notes` |

## 数据

当前 CSV 仅包含表头，暂无数据行。

---
免责声明：本文仅用于智能投研系统知识库迁移与测试，不构成投资建议。投资有风险，入市需谨慎。
