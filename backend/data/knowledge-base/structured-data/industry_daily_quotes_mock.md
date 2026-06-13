# 结构化数据：industry_daily_quotes_mock

> 迁移说明：本文由现有知识库资料转换为 Markdown，用于智能投研 demo、RAG 检索、结构化证据追溯和评测。本文不构成投资建议。

## 迁移元数据

| 字段 | 内容 |
|---|---|
| 资料类型 | structured_csv |
| 原始路径 | data/metadata/industry_daily_quotes_mock.csv |
| 迁移后目录 | structured-data |
| 迁移文件 | industry_daily_quotes_mock.md |

## 数据表说明

- 原始路径：`data/metadata/industry_daily_quotes_mock.csv`
- 字段数量：10
- 数据行数：35
- mock 标记统计：`is_mock=true` 35 行，`is_mock=false` 0 行。
- 使用约束：`is_mock=true` 的行仅用于 demo 链路演示或字段补齐，不得作为真实行情、财务或估值事实直接对用户表述。

## 字段

| 序号 | 字段名 |
|---:|---|
| 1 | `trade_date` |
| 2 | `industry_id` |
| 3 | `industry_name` |
| 4 | `close_point` |
| 5 | `pct_change` |
| 6 | `turnover_amount` |
| 7 | `amount_unit` |
| 8 | `source` |
| 9 | `is_mock` |
| 10 | `notes` |

## 数据

| trade_date | industry_id | industry_name | close_point | pct_change | turnover_amount | amount_unit | source | is_mock | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-22 | industry_baijiu | 白酒行业 | 2180.4 | 0.72 | 82100000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-23 | industry_baijiu | 白酒行业 | 2222.7 | 1.94 | 94500000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-24 | industry_baijiu | 白酒行业 | 2205.3 | -0.78 | 80400000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-27 | industry_baijiu | 白酒行业 | 2148.9 | -2.56 | 103200000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-28 | industry_baijiu | 白酒行业 | 2160.6 | 0.54 | 75200000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-29 | industry_baijiu | 白酒行业 | 2171.2 | 0.49 | 73100000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-30 | industry_baijiu | 白酒行业 | 2165.4 | -0.27 | 74600000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-22 | industry_condiment | 调味品行业 | 1318.5 | 0.28 | 22600000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-23 | industry_condiment | 调味品行业 | 1326.7 | 0.62 | 24100000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-24 | industry_condiment | 调味品行业 | 1317.1 | -0.72 | 21800000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-27 | industry_condiment | 调味品行业 | 1309.4 | -0.58 | 22900000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-28 | industry_condiment | 调味品行业 | 1314.8 | 0.41 | 20500000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-29 | industry_condiment | 调味品行业 | 1321.6 | 0.52 | 21300000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-30 | industry_condiment | 调味品行业 | 1318.2 | -0.26 | 20700000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-22 | industry_chip | 芯片 | 3890.2 | 2.74 | 158600000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-23 | industry_chip | 芯片 | 4011.8 | 3.13 | 178300000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-24 | industry_chip | 芯片 | 4062.5 | 1.26 | 169900000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-27 | industry_chip | 芯片 | 4169.7 | 2.64 | 192200000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-28 | industry_chip | 芯片 | 4318.4 | 3.57 | 211400000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-29 | industry_chip | 芯片 | 4395.0 | 1.77 | 204800000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-30 | industry_chip | 芯片 | 4456.8 | 1.41 | 218000000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-22 | industry_textile | 纺织业 | 962.8 | 0.18 | 9800000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-23 | industry_textile | 纺织业 | 966.7 | 0.41 | 10300000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-24 | industry_textile | 纺织业 | 960.4 | -0.65 | 9700000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-27 | industry_textile | 纺织业 | 956.6 | -0.40 | 9400000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-28 | industry_textile | 纺织业 | 959.2 | 0.27 | 9100000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-29 | industry_textile | 纺织业 | 963.1 | 0.41 | 9300000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-30 | industry_textile | 纺织业 | 961.0 | -0.22 | 8900000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-22 | industry_new_energy_battery | 新能源电池 | 2865.4 | 1.85 | 128400000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-23 | industry_new_energy_battery | 新能源电池 | 2926.2 | 2.12 | 141200000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-24 | industry_new_energy_battery | 新能源电池 | 2951.3 | 0.86 | 136800000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-27 | industry_new_energy_battery | 新能源电池 | 3008.0 | 1.92 | 149600000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-28 | industry_new_energy_battery | 新能源电池 | 3057.5 | 1.65 | 156300000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-29 | industry_new_energy_battery | 新能源电池 | 3080.4 | 0.75 | 151700000000 | CNY | mock_demo | true | 演示用mock板块行情 |
| 2026-04-30 | industry_new_energy_battery | 新能源电池 | 3022.2 | -1.89 | 163500000000 | CNY | mock_demo | true | 演示用mock板块行情 |

---
免责声明：本文仅用于智能投研系统知识库迁移与测试，不构成投资建议。投资有风险，入市需谨慎。
