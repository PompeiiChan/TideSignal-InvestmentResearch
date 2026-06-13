# 结构化数据：industries

> 迁移说明：本文由现有知识库资料转换为 Markdown，用于智能投研 demo、RAG 检索、结构化证据追溯和评测。本文不构成投资建议。

## 迁移元数据

| 字段 | 内容 |
|---|---|
| 资料类型 | structured_csv |
| 原始路径 | data/metadata/industries.csv |
| 迁移后目录 | structured-data |
| 迁移文件 | industries.md |

## 数据表说明

- 原始路径：`data/metadata/industries.csv`
- 字段数量：4
- 数据行数：9
- mock 标记统计：该表无 `is_mock` 字段，请结合表名、字段和备注判断用途。

## 字段

| 序号 | 字段名 |
|---:|---|
| 1 | `industry_id` |
| 2 | `industry_name` |
| 3 | `parent_sector` |
| 4 | `description` |

## 数据

| industry_id | industry_name | parent_sector | description |
| --- | --- | --- | --- |
| industry_baijiu | 白酒行业 | 食品饮料 | 以白酒生产销售为核心的消费品行业 |
| industry_condiment | 调味品行业 | 食品饮料 | 以酱油等复合调味品生产销售为核心的消费品行业 |
| industry_chip | 芯片 | 电子 | 覆盖半导体设计、制造、封测及AI算力芯片等环节 |
| industry_textile | 纺织业 | 轻工制造 | 覆盖纺织制造、家纺和服饰相关产业链 |
| industry_new_energy_battery | 新能源电池 | 电力设备 | 覆盖动力电池、储能电池及上游材料产业链 |
| industry_insurance | 保险 | 行业资料 | 用于 RAG 行业检索与评测的保险行业资料 |
| industry_building_materials | 建材 | 行业资料 | 用于 RAG 行业检索与评测的建材和玻璃纤维行业资料 |
| industry_machinery | 机械 | 行业资料 | 用于 RAG 行业检索与评测的机械设备行业资料 |
| industry_home_appliance | 家电 | 行业资料 | 用于 RAG 行业检索与评测的家电行业资料 |

---
免责声明：本文仅用于智能投研系统知识库迁移与测试，不构成投资建议。投资有风险，入市需谨慎。
