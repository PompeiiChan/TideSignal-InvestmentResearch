# 结构化数据：document_manifest.example

> 迁移说明：本文由现有知识库资料转换为 Markdown，用于智能投研 demo、RAG 检索、结构化证据追溯和评测。本文不构成投资建议。

## 迁移元数据

| 字段 | 内容 |
|---|---|
| 资料类型 | structured_csv |
| 原始路径 | data/metadata/document_manifest.example.csv |
| 迁移后目录 | structured-data |
| 迁移文件 | document_manifest.example.md |

## 数据表说明

- 原始路径：`data/metadata/document_manifest.example.csv`
- 字段数量：11
- 数据行数：5
- mock 标记统计：`is_mock=true` 0 行，`is_mock=false` 5 行。
- 使用约束：`is_mock=true` 的行仅用于 demo 链路演示或字段补齐，不得作为真实行情、财务或估值事实直接对用户表述。

## 字段

| 序号 | 字段名 |
|---:|---|
| 1 | `doc_id` |
| 2 | `doc_type` |
| 3 | `title` |
| 4 | `company_id` |
| 5 | `industry_id` |
| 6 | `period` |
| 7 | `publish_date` |
| 8 | `source` |
| 9 | `file_path` |
| 10 | `is_mock` |
| 11 | `notes` |

## 数据

| doc_id | doc_type | title | company_id | industry_id | period | publish_date | source | file_path | is_mock | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ann_000568_2025 | annual_report | 泸州老窖2025年年度报告 | company_000568 | industry_baijiu | 2025A | 2026-04-30 | 公司公告 | data/raw/company_reports/000568_SZ_泸州老窖/annual/2025_年报_泸州老窖_000568.SZ.pdf | false | 示例行，复制到 document_manifest.csv 后请确认日期和文件名 |
| q1_300750_2026 | quarterly_report | 宁德时代2026年第一季度报告 | company_300750 | industry_new_energy_battery | 2026Q1 | 2026-04-30 | 公司公告 | data/raw/company_reports/300750_SZ_宁德时代/quarterly/2026Q1_一季报_宁德时代_300750.SZ.pdf | false | 示例行，复制到 document_manifest.csv 后请确认日期和文件名 |
| research_688256_20260420 | company_research | 寒武纪公司点评 | company_688256 | industry_chip |  | 2026-04-20 | 券商研报 | data/raw/company_reports/688256_SH_寒武纪/research/2026-04-20_某券商_寒武纪公司点评.pdf | false | 示例行，来源请填真实券商或资料来源 |
| industry_battery_20260415 | industry_research | 新能源电池行业跟踪 |  | industry_new_energy_battery |  | 2026-04-15 | 券商研报 | data/raw/industry_reports/新能源电池/2026-04-15_某券商_新能源电池行业跟踪.pdf | false | 示例行，行业报告可不填 company_id |
| event_ashare_20260430 | market_event | 2026年4月A股热点整理 |  |  |  | 2026-04-30 | 人工整理 | data/raw/market_events/2026-04_A股热点/2026-04-30_热点整理_A股四月主线.md | false | 示例行，热点整理可以是 Markdown 或 PDF |

---
免责声明：本文仅用于智能投研系统知识库迁移与测试，不构成投资建议。投资有风险，入市需谨慎。
