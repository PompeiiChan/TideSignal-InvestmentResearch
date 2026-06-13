# 结构化数据：interval_performance_mock

> 迁移说明：本文由现有知识库资料转换为 Markdown，用于智能投研 demo、RAG 检索、结构化证据追溯和评测。本文不构成投资建议。

## 迁移元数据

| 字段 | 内容 |
|---|---|
| 资料类型 | structured_csv |
| 原始路径 | data/metadata/interval_performance_mock.csv |
| 迁移后目录 | structured-data |
| 迁移文件 | interval_performance_mock.md |

## 数据表说明

- 原始路径：`data/metadata/interval_performance_mock.csv`
- 字段数量：12
- 数据行数：14
- mock 标记统计：`is_mock=true` 14 行，`is_mock=false` 0 行。
- 使用约束：`is_mock=true` 的行仅用于 demo 链路演示或字段补齐，不得作为真实行情、财务或估值事实直接对用户表述。

## 字段

| 序号 | 字段名 |
|---:|---|
| 1 | `object_type` |
| 2 | `object_id` |
| 3 | `object_name` |
| 4 | `period` |
| 5 | `start_date` |
| 6 | `end_date` |
| 7 | `pct_change` |
| 8 | `turnover_amount` |
| 9 | `amount_unit` |
| 10 | `source` |
| 11 | `is_mock` |
| 12 | `notes` |

## 数据

| object_type | object_id | object_name | period | start_date | end_date | pct_change | turnover_amount | amount_unit | source | is_mock | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stock | company_000568 | 泸州老窖 | 5d | 2026-04-24 | 2026-04-30 | -1.91 | 12560000000 | CNY | mock_demo | true | 演示用mock区间表现 |
| stock | company_603288 | 海天味业 | 5d | 2026-04-24 | 2026-04-30 | -0.12 | 4956000000 | CNY | mock_demo | true | 演示用mock区间表现 |
| stock | company_688256 | 寒武纪 | 5d | 2026-04-24 | 2026-04-30 | 10.49 | 55840000000 | CNY | mock_demo | true | 演示用mock区间表现 |
| stock | company_002293 | 罗莱生活 | 5d | 2026-04-24 | 2026-04-30 | -0.10 | 630000000 | CNY | mock_demo | true | 演示用mock区间表现 |
| stock | company_300750 | 宁德时代 | 5d | 2026-04-24 | 2026-04-30 | 2.89 | 62440000000 | CNY | mock_demo | true | 演示用mock区间表现 |
| index | 000001.SH | 上证指数 | 5d | 2026-04-24 | 2026-04-30 | 0.92 | 2819000000000 | CNY | mock_demo | true | 演示用mock区间表现 |
| index | 399006.SZ | 创业板指 | 5d | 2026-04-24 | 2026-04-30 | 2.75 | 2238000000000 | CNY | mock_demo | true | 演示用mock区间表现 |
| index | 000688.SH | 科创50 | 5d | 2026-04-24 | 2026-04-30 | 9.22 | 756000000000 | CNY | mock_demo | true | 演示用mock区间表现 |
| index | 000300.SH | 沪深300 | 5d | 2026-04-24 | 2026-04-30 | 1.25 | 2054000000000 | CNY | mock_demo | true | 演示用mock区间表现 |
| industry | industry_baijiu | 白酒行业 | 5d | 2026-04-24 | 2026-04-30 | -1.81 | 408500000000 | CNY | mock_demo | true | 演示用mock区间表现 |
| industry | industry_condiment | 调味品行业 | 5d | 2026-04-24 | 2026-04-30 | 0.08 | 107200000000 | CNY | mock_demo | true | 演示用mock区间表现 |
| industry | industry_chip | 芯片 | 5d | 2026-04-24 | 2026-04-30 | 9.71 | 996300000000 | CNY | mock_demo | true | 演示用mock区间表现 |
| industry | industry_textile | 纺织业 | 5d | 2026-04-24 | 2026-04-30 | 0.06 | 45400000000 | CNY | mock_demo | true | 演示用mock区间表现 |
| industry | industry_new_energy_battery | 新能源电池 | 5d | 2026-04-24 | 2026-04-30 | 2.40 | 757900000000 | CNY | mock_demo | true | 演示用mock区间表现 |

---
免责声明：本文仅用于智能投研系统知识库迁移与测试，不构成投资建议。投资有风险，入市需谨慎。
