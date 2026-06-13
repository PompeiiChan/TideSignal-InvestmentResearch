# 结构化数据：valuation_metrics_template

> 迁移说明：本文由现有知识库资料转换为 Markdown，用于智能投研 demo、RAG 检索、结构化证据追溯和评测。本文不构成投资建议。

## 迁移元数据

| 字段 | 内容 |
|---|---|
| 资料类型 | structured_csv |
| 原始路径 | data/metadata/valuation_metrics_template.csv |
| 迁移后目录 | structured-data |
| 迁移文件 | valuation_metrics_template.md |

## 数据表说明

- 原始路径：`data/metadata/valuation_metrics_template.csv`
- 字段数量：21
- 数据行数：0
- mock 标记统计：`is_mock=true` 0 行，`is_mock=false` 0 行。
- 使用约束：`is_mock=true` 的行仅用于 demo 链路演示或字段补齐，不得作为真实行情、财务或估值事实直接对用户表述。

## 字段

| 序号 | 字段名 |
|---:|---|
| 1 | `company_id` |
| 2 | `as_of_date` |
| 3 | `ticker` |
| 4 | `company_name` |
| 5 | `close_price` |
| 6 | `pct_change` |
| 7 | `pe_ttm` |
| 8 | `pe_static` |
| 9 | `pb_lf` |
| 10 | `ps_ttm` |
| 11 | `market_cap` |
| 12 | `float_market_cap` |
| 13 | `dividend_yield` |
| 14 | `valuation_percentile` |
| 15 | `pe_valuation_percentile` |
| 16 | `pb_valuation_percentile` |
| 17 | `ps_valuation_percentile` |
| 18 | `currency` |
| 19 | `source` |
| 20 | `is_mock` |
| 21 | `notes` |

## 数据

当前 CSV 仅包含表头，暂无数据行。

---
免责声明：本文仅用于智能投研系统知识库迁移与测试，不构成投资建议。投资有风险，入市需谨慎。
