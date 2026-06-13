# 结构化数据：valuation_metrics_choice_demo

> 迁移说明：本文由现有知识库资料转换为 Markdown，用于智能投研 demo、RAG 检索、结构化证据追溯和评测。本文不构成投资建议。

## 迁移元数据

| 字段 | 内容 |
|---|---|
| 资料类型 | structured_csv |
| 原始路径 | data/metadata/valuation_metrics_choice_demo.csv |
| 迁移后目录 | structured-data |
| 迁移文件 | valuation_metrics_choice_demo.md |

## 数据表说明

- 原始路径：`data/metadata/valuation_metrics_choice_demo.csv`
- 字段数量：21
- 数据行数：6
- mock 标记统计：`is_mock=true` 0 行，`is_mock=false` 6 行。
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

| company_id | as_of_date | ticker | company_name | close_price | pct_change | pe_ttm | pe_static | pb_lf | ps_ttm | market_cap | float_market_cap | dividend_yield | valuation_percentile | pe_valuation_percentile | pb_valuation_percentile | ps_valuation_percentile | currency | source | is_mock | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| company_000568 | 2026-04-29 | 000568.SZ | 泸州老窖 | 101.73 | 1.53 | 15.05 | 13.83 | 2.90 | 6.14 | 149741000000 | 149671000000 |  |  |  |  |  | CNY | 东方财富Choice数据 | false | 用户补充demo估值数据；股息率和估值分位待补 |
| company_688256 | 2026-04-30 | 688256.SH | 寒武纪 | 1699.96 | 20.00 | 263.84 | 348.11 | 55.69 |  | 716848000000 | 716848000000 |  |  |  |  |  | CNY | 东方财富Choice数据 | false | 用户补充demo估值数据；PS、股息率和估值分位待补 |
| company_002293 | 2026-04-30 | 002293.SZ | 罗莱生活 | 11.26 | 2.18 | 16.94 | 18.06 | 2.16 | 1.92 | 9389000000 | 9307000000 |  |  |  |  |  | CNY | 东方财富Choice数据 | false | 用户补充demo估值数据；股息率和估值分位待补 |
| company_002293 | 2026-04-29 | 002293.SZ | 罗莱生活 | 11.02 | 0.55 | 16.58 | 17.68 | 2.12 | 1.87 | 9189000000 | 9109000000 |  |  |  |  |  | CNY | 东方财富Choice数据 | false | 用户补充demo估值数据；股息率和估值分位待补 |
| company_300750 | 2026-04-30 | 300750.SZ | 宁德时代 | 436.00 | -2.02 | 25.54 | 27.94 | 5.65 |  | 2020000000000 | 1860000000000 |  |  |  |  |  | CNY | 东方财富Choice数据 | false | 用户补充demo估值数据；PS、股息率和估值分位待补 |
| company_300750 | 2026-04-29 | 300750.SZ | 宁德时代 | 445.00 | 4.05 | 25.72 | 28.13 | 5.68 |  | 2030000000000 | 1890000000000 |  |  |  |  |  | CNY | 东方财富Choice数据 | false | 用户补充demo估值数据；PS、股息率和估值分位待补 |

---
免责声明：本文仅用于智能投研系统知识库迁移与测试，不构成投资建议。投资有风险，入市需谨慎。
