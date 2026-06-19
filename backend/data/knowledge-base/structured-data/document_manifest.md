# 结构化数据：document_manifest

> 迁移说明：本文由现有知识库资料转换为 Markdown，用于智能投研 demo、RAG 检索、结构化证据追溯和评测。本文不构成投资建议。

## 迁移元数据

| 字段 | 内容 |
|---|---|
| 资料类型 | structured_csv |
| 原始路径 | data/metadata/document_manifest.csv |
| 迁移后目录 | structured-data |
| 迁移文件 | document_manifest.md |

## 数据表说明

- 原始路径：`data/metadata/document_manifest.csv`
- 字段数量：11
- 数据行数：223
- mock 标记统计：`is_mock=true` 0 行，`is_mock=false` 223 行。
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
| ann_000568_2025 | annual_report | 泸州老窖2025年年度报告 | company_000568 | industry_baijiu | 2025A |  | 公司公告 | data/raw/company_reports/000568_SZ_泸州老窖/annual/2025_年报_泸州老窖_000568.SZ.pdf | false | 用户提供PDF |
| q1_000568_2026 | quarterly_report | 泸州老窖2026年第一季度报告 | company_000568 | industry_baijiu | 2026Q1 |  | 公司公告 | data/raw/company_reports/000568_SZ_泸州老窖/quarterly/2026Q1_一季报_泸州老窖_000568.SZ.pdf | false | 用户提供PDF |
| ann_603288_2025 | annual_report | 海天味业2025年年度报告 | company_603288 | industry_condiment | 2025A |  | 公司公告 | data/raw/company_reports/603288_SH_海天味业/annual/2025_年报_海天味业_603288.SH.pdf | false | 用户提供PDF |
| q1_603288_2026 | quarterly_report | 海天味业2026年第一季度报告 | company_603288 | industry_condiment | 2026Q1 |  | 公司公告 | data/raw/company_reports/603288_SH_海天味业/quarterly/2026Q1_一季报_海天味业_603288.SH.pdf | false | 用户提供PDF |
| ann_688256_2025 | annual_report | 寒武纪2025年年度报告 | company_688256 | industry_chip | 2025A |  | 公司公告 | data/raw/company_reports/688256_SH_寒武纪/annual/2025_年报_寒武纪_688256.SH.pdf | false | 用户提供PDF |
| q1_688256_2026 | quarterly_report | 寒武纪2026年第一季度报告 | company_688256 | industry_chip | 2026Q1 |  | 公司公告 | data/raw/company_reports/688256_SH_寒武纪/quarterly/2026Q1_一季报_寒武纪_688256.SH.pdf | false | 用户提供PDF |
| ann_002293_2025 | annual_report | 罗莱生活2025年年度报告 | company_002293 | industry_textile | 2025A |  | 公司公告 | data/raw/company_reports/002293_SZ_罗莱生活/annual/2025_年报_罗莱生活_002293.SZ.pdf | false | 用户提供PDF |
| q1_002293_2026 | quarterly_report | 罗莱生活2026年第一季度报告 | company_002293 | industry_textile | 2026Q1 |  | 公司公告 | data/raw/company_reports/002293_SZ_罗莱生活/quarterly/2026Q1_一季报_罗莱生活_002293.SZ.pdf | false | 用户提供PDF |
| ann_300750_2025 | annual_report | 宁德时代2025年年度报告 | company_300750 | industry_new_energy_battery | 2025A |  | 公司公告 | data/raw/company_reports/300750_SZ_宁德时代/annual/2025_年报_宁德时代_300750.SZ.pdf | false | 用户提供PDF |
| q1_300750_2026 | quarterly_report | 宁德时代2026年第一季度报告 | company_300750 | industry_new_energy_battery | 2026Q1 |  | 公司公告 | data/raw/company_reports/300750_SZ_宁德时代/quarterly/2026Q1_一季报_宁德时代_300750.SZ.pdf | false | 用户提供PDF |
| research_000568_guosen | company_research | 泸州老窖公司研报：以消费者为中心数字化赋能供应链 | company_000568 | industry_baijiu |  |  | 国信证券 | data/raw/company_reports/000568_SZ_泸州老窖/research/国信证券_泸州老窖_以消费者为中心数字化赋能供应链.pdf | false | 用户提供PDF |
| research_603288_bocom | company_research | 海天味业公司研报：调味品龙头海外市场成长空间 | company_603288 | industry_condiment |  |  | 交银国际 | data/raw/company_reports/603288_SH_海天味业/research/交银国际_海天味业_调味品龙头海外市场成长空间.pdf | false | 用户提供PDF |
| research_688256_huachuang | company_research | 寒武纪公司研报：国产AI芯片领军者云边端核心壁垒 | company_688256 | industry_chip |  |  | 华创证券 | data/raw/company_reports/688256_SH_寒武纪/research/华创证券_寒武纪_国产AI芯片领军者云边端核心壁垒.pdf | false | 用户提供PDF |
| research_002293_gf | company_research | 罗莱生活公司研报：产品渠道供应链营销齐发力 | company_002293 | industry_textile |  |  | 广发证券 | data/raw/company_reports/002293_SZ_罗莱生活/research/广发证券_罗莱生活_产品渠道供应链营销齐发力.pdf | false | 用户提供PDF |
| research_300750_dwzq | company_research | 宁德时代公司研报：技术迭代引领行业盈利规模共振 | company_300750 | industry_new_energy_battery |  |  | 东吴证券 | data/raw/company_reports/300750_SZ_宁德时代/research/东吴证券_宁德时代_技术迭代引领行业盈利规模共振.pdf | false | 用户提供PDF |
| event_ashare_202604 | market_event | 2026年4月A股热点事件整理 |  |  | 2026-04 | 2026-05-11 | 公开资讯整理 | backend/data/knowledge-base/hotspots/2026-04-market-hotspots.md | false | 月度市场热点，供RAG与hotspot_agent使用 |
| event_ashare_202605 | market_event | 2026年5月A股月度热点：硬科技先扬后抑，AI算力、半导体、PCB、人形机器人与新能源链轮动分化 |  |  | 2026-05 | 2026-06-11 | 财经媒体复盘、政策/监管公开信息 | backend/data/knowledge-base/hotspots/2026-05-market-hotspots.md | false | 完整5月收官复盘，联网整理，is_mock=false |
| event_ashare_202606 | market_event | 2026年6月A股阶段性热点：AI硬件冲高后分化，半导体退潮，红利金融与煤炭承接避险 |  |  | 2026-06 | 2026-06-11 | 财经媒体复盘、政策/监管公开信息 | backend/data/knowledge-base/hotspots/2026-06-market-hotspots.md | false | 截至2026-06-11的阶段性月报，6月未结束 |
| industry_baijiu_cms_2026 | industry_research | 白酒行业研报：2026年度投资策略底部更加积极 |  | industry_baijiu |  |  | 招商证券 | data/raw/industry_reports/白酒行业/招商证券_白酒行业_2026年度投资策略底部更加积极.pdf | false | 用户提供PDF |
| industry_condiment_qince_2025 | industry_research | 调味品行业研报：2025年中国调味品行业报告 |  | industry_condiment |  |  | 勤策消费研究 | data/raw/industry_reports/调味品行业/勤策消费研究_调味品行业_2025年中国调味品行业报告.pdf | false | 用户提供PDF |
| industry_chip_huachuang_gpu | industry_research | 芯片行业研报：算力革命与国产GPU |  | industry_chip |  |  | 华创证券 | data/raw/industry_reports/芯片/华创证券_芯片行业_算力革命与国产GPU.pdf | false | 用户提供PDF |
| industry_textile_orient_sleep | industry_research | 纺织业研报：睡眠经济与家纺行业新机遇 |  | industry_textile |  |  | 东方证券 | data/raw/industry_reports/纺织业/东方证券_纺织业_睡眠经济与家纺行业新机遇.pdf | false | 用户提供PDF |
| industry_battery_caixin_solid | industry_research | 新能源电池行业研报：产业上行周期与固态产业化 |  | industry_new_energy_battery |  |  | 财信证券 | data/raw/industry_reports/新能源电池/财信证券_新能源电池行业_产业上行周期与固态产业化.pdf | false | 用户提供PDF |
| insurance_ccxi_2026q1 | industry_research | 保险资管行业研报：2026Q1创新型产品观察与展望 |  | industry_insurance | 2026Q1 |  | 中诚信国际 | data/raw/industry_reports/保险/中诚信国际_保险资管行业_2026Q1创新型产品观察与展望.pdf | false | 行业研报资料，供 RAG 行业检索与评测使用 |
| insurance_ky_20260409 | industry_research | 保险行业研报：资产向好驱动业绩高增 |  | industry_insurance |  | 2026-04-09 | 开源证券 | data/raw/industry_reports/保险/开源证券_保险行业_资产向好驱动业绩高增.pdf | false | 行业研报资料，供 RAG 行业检索与评测使用 |
| building_materials_dgzq_20260330 | industry_research | 建材行业研报：玻璃纤维周期复苏与结构增长 |  | industry_building_materials |  | 2026-03-30 | 东莞证券 | data/raw/industry_reports/建材/东莞证券_建材行业_玻璃纤维周期复苏与结构增长.pdf | false | 行业研报资料，供 RAG 行业检索与评测使用 |
| machinery_gjzq_20260509 | industry_research | 机械行业研报：燃气轮机商业航天工程机械 |  | industry_machinery |  | 2026-05-09 | 国金证券 | data/raw/industry_reports/机械/国金证券_机械行业_燃气轮机商业航天工程机械.pdf | false | 行业研报资料，供 RAG 行业检索与评测使用 |
| home_appliance_20260505 | industry_research | 家电行业研报：白电黑电厨电小家电景气跟踪 |  | industry_home_appliance |  | 2026-05-05 | 未知来源 | data/raw/industry_reports/家电/家电行业_白电黑电厨电小家电景气跟踪.pdf | false | 行业研报资料，供 RAG 行业检索与评测使用 |

---
免责声明：本文仅用于智能投研系统知识库迁移与测试，不构成投资建议。投资有风险，入市需谨慎。
| q1_300007_2026 | quarterly_report | 汉威科技2026年第一季度报告 | company_300007 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300007-chinext-300007-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300007_2025 | annual_report | 汉威科技2025年年度报告 | company_300007 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300007-chinext-300007-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300007_2024 | annual_report | 汉威科技2024年年度报告 | company_300007 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300007-chinext-300007-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300007_2023 | annual_report | 汉威科技2023年年度报告 | company_300007 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300007-chinext-300007-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300014_2026 | quarterly_report | 亿纬锂能2026年第一季度报告 | company_300014 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300014-chinext-300014-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300014_2025 | annual_report | 亿纬锂能2025年年度报告 | company_300014 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300014-chinext-300014-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300014_2024 | annual_report | 亿纬锂能2024年年度报告 | company_300014 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300014-chinext-300014-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300014_2023 | annual_report | 亿纬锂能2023年年度报告 | company_300014 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300014-chinext-300014-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300015_2026 | quarterly_report | 爱尔眼科2026年第一季度报告 | company_300015 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300015-chinext-300015-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300015_2025 | annual_report | 爱尔眼科2025年年度报告 | company_300015 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300015-chinext-300015-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300015_2024 | annual_report | 爱尔眼科2024年年度报告 | company_300015 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300015-chinext-300015-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300015_2023 | annual_report | 爱尔眼科2023年年度报告 | company_300015 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300015-chinext-300015-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300019_2026 | quarterly_report | 硅宝科技2026年第一季度报告 | company_300019 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300019-chinext-300019-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300019_2025 | annual_report | 硅宝科技2025年年度报告 | company_300019 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300019-chinext-300019-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300019_2024 | annual_report | 硅宝科技2024年年度报告 | company_300019 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300019-chinext-300019-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300019_2023 | annual_report | 硅宝科技2023年年度报告 | company_300019 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300019-chinext-300019-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q_300023_20250630 | quarterly_report | 宝德退2025年06月30日报告 | company_300023 | industry_chinext | 2025Q2 |  | 新浪财经公开 API | data/knowledge-base/financials/300023-chinext-300023-financial-2025Q2-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300023_2025 | annual_report | 宝德退2025年年度报告 | company_300023 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300023-chinext-300023-financial-2025Q2-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300023_2024 | annual_report | 宝德退2024年年度报告 | company_300023 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300023-chinext-300023-financial-2025Q2-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300023_2023 | annual_report | 宝德退2023年年度报告 | company_300023 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300023-chinext-300023-financial-2025Q2-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300030_2026 | quarterly_report | 阳普医疗2026年第一季度报告 | company_300030 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300030-chinext-300030-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300030_2025 | annual_report | 阳普医疗2025年年度报告 | company_300030 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300030-chinext-300030-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300030_2024 | annual_report | 阳普医疗2024年年度报告 | company_300030 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300030-chinext-300030-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300030_2023 | annual_report | 阳普医疗2023年年度报告 | company_300030 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300030-chinext-300030-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300033_2026 | quarterly_report | 同花顺2026年第一季度报告 | company_300033 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300033-chinext-300033-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300033_2025 | annual_report | 同花顺2025年年度报告 | company_300033 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300033-chinext-300033-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300033_2024 | annual_report | 同花顺2024年年度报告 | company_300033 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300033-chinext-300033-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300033_2023 | annual_report | 同花顺2023年年度报告 | company_300033 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300033-chinext-300033-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300048_2026 | quarterly_report | 合康新能2026年第一季度报告 | company_300048 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300048-chinext-300048-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300048_2025 | annual_report | 合康新能2025年年度报告 | company_300048 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300048-chinext-300048-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300048_2024 | annual_report | 合康新能2024年年度报告 | company_300048 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300048-chinext-300048-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300048_2023 | annual_report | 合康新能2023年年度报告 | company_300048 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300048-chinext-300048-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300053_2026 | quarterly_report | 航宇微2026年第一季度报告 | company_300053 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300053-chinext-300053-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300053_2025 | annual_report | 航宇微2025年年度报告 | company_300053 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300053-chinext-300053-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300053_2024 | annual_report | 航宇微2024年年度报告 | company_300053 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300053-chinext-300053-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300053_2023 | annual_report | 航宇微2023年年度报告 | company_300053 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300053-chinext-300053-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300057_2026 | quarterly_report | 万顺新材2026年第一季度报告 | company_300057 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300057-chinext-300057-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300057_2025 | annual_report | 万顺新材2025年年度报告 | company_300057 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300057-chinext-300057-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300057_2024 | annual_report | 万顺新材2024年年度报告 | company_300057 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300057-chinext-300057-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300057_2023 | annual_report | 万顺新材2023年年度报告 | company_300057 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300057-chinext-300057-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300061_2026 | quarterly_report | 旗天科技2026年第一季度报告 | company_300061 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300061-chinext-300061-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300061_2025 | annual_report | 旗天科技2025年年度报告 | company_300061 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300061-chinext-300061-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300061_2024 | annual_report | 旗天科技2024年年度报告 | company_300061 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300061-chinext-300061-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300061_2023 | annual_report | 旗天科技2023年年度报告 | company_300061 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300061-chinext-300061-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300074_2026 | quarterly_report | 华平股份2026年第一季度报告 | company_300074 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300074-chinext-300074-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300074_2025 | annual_report | 华平股份2025年年度报告 | company_300074 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300074-chinext-300074-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300074_2024 | annual_report | 华平股份2024年年度报告 | company_300074 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300074-chinext-300074-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300074_2023 | annual_report | 华平股份2023年年度报告 | company_300074 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300074-chinext-300074-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300076_2026 | quarterly_report | *ST宁视2026年第一季度报告 | company_300076 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300076-chinext-300076-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300076_2025 | annual_report | *ST宁视2025年年度报告 | company_300076 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300076-chinext-300076-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300076_2024 | annual_report | *ST宁视2024年年度报告 | company_300076 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300076-chinext-300076-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300076_2023 | annual_report | *ST宁视2023年年度报告 | company_300076 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300076-chinext-300076-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300077_2026 | quarterly_report | 国民技术2026年第一季度报告 | company_300077 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300077-chinext-300077-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300077_2025 | annual_report | 国民技术2025年年度报告 | company_300077 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300077-chinext-300077-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300077_2024 | annual_report | 国民技术2024年年度报告 | company_300077 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300077-chinext-300077-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300077_2023 | annual_report | 国民技术2023年年度报告 | company_300077 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300077-chinext-300077-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300085_2026 | quarterly_report | 银之杰2026年第一季度报告 | company_300085 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300085-chinext-300085-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300085_2025 | annual_report | 银之杰2025年年度报告 | company_300085 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300085-chinext-300085-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300085_2024 | annual_report | 银之杰2024年年度报告 | company_300085 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300085-chinext-300085-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300085_2023 | annual_report | 银之杰2023年年度报告 | company_300085 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300085-chinext-300085-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300090_2026 | quarterly_report | 盛运退2026年第一季度报告 | company_300090 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300090-chinext-300090-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300090_2025 | annual_report | 盛运退2025年年度报告 | company_300090 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300090-chinext-300090-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300090_2024 | annual_report | 盛运退2024年年度报告 | company_300090 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300090-chinext-300090-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300090_2023 | annual_report | 盛运退2023年年度报告 | company_300090 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300090-chinext-300090-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300092_2026 | quarterly_report | 科新机电2026年第一季度报告 | company_300092 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300092-chinext-300092-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300092_2025 | annual_report | 科新机电2025年年度报告 | company_300092 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300092-chinext-300092-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300092_2024 | annual_report | 科新机电2024年年度报告 | company_300092 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300092-chinext-300092-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300092_2023 | annual_report | 科新机电2023年年度报告 | company_300092 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300092-chinext-300092-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300104_2026 | quarterly_report | 乐视退2026年第一季度报告 | company_300104 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300104-chinext-300104-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300104_2025 | annual_report | 乐视退2025年年度报告 | company_300104 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300104-chinext-300104-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300104_2024 | annual_report | 乐视退2024年年度报告 | company_300104 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300104-chinext-300104-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300104_2023 | annual_report | 乐视退2023年年度报告 | company_300104 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300104-chinext-300104-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300105_2026 | quarterly_report | 龙源技术2026年第一季度报告 | company_300105 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300105-chinext-300105-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300105_2025 | annual_report | 龙源技术2025年年度报告 | company_300105 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300105-chinext-300105-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300105_2024 | annual_report | 龙源技术2024年年度报告 | company_300105 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300105-chinext-300105-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300105_2023 | annual_report | 龙源技术2023年年度报告 | company_300105 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300105-chinext-300105-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300109_2026 | quarterly_report | 新开源2026年第一季度报告 | company_300109 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300109-chinext-300109-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300109_2025 | annual_report | 新开源2025年年度报告 | company_300109 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300109-chinext-300109-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300109_2024 | annual_report | 新开源2024年年度报告 | company_300109 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300109-chinext-300109-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300109_2023 | annual_report | 新开源2023年年度报告 | company_300109 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300109-chinext-300109-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300113_2026 | quarterly_report | 顺网科技2026年第一季度报告 | company_300113 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300113-chinext-300113-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300113_2025 | annual_report | 顺网科技2025年年度报告 | company_300113 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300113-chinext-300113-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300113_2024 | annual_report | 顺网科技2024年年度报告 | company_300113 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300113-chinext-300113-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300113_2023 | annual_report | 顺网科技2023年年度报告 | company_300113 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300113-chinext-300113-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300119_2026 | quarterly_report | 瑞普生物2026年第一季度报告 | company_300119 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300119-chinext-300119-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300119_2025 | annual_report | 瑞普生物2025年年度报告 | company_300119 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300119-chinext-300119-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300119_2024 | annual_report | 瑞普生物2024年年度报告 | company_300119 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300119-chinext-300119-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300119_2023 | annual_report | 瑞普生物2023年年度报告 | company_300119 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300119-chinext-300119-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300128_2026 | quarterly_report | 锦富技术2026年第一季度报告 | company_300128 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300128-chinext-300128-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300128_2025 | annual_report | 锦富技术2025年年度报告 | company_300128 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300128-chinext-300128-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300128_2024 | annual_report | 锦富技术2024年年度报告 | company_300128 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300128-chinext-300128-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300128_2023 | annual_report | 锦富技术2023年年度报告 | company_300128 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300128-chinext-300128-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300129_2026 | quarterly_report | 泰胜风能2026年第一季度报告 | company_300129 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300129-chinext-300129-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300129_2025 | annual_report | 泰胜风能2025年年度报告 | company_300129 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300129-chinext-300129-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300129_2024 | annual_report | 泰胜风能2024年年度报告 | company_300129 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300129-chinext-300129-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300129_2023 | annual_report | 泰胜风能2023年年度报告 | company_300129 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300129-chinext-300129-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300141_2026 | quarterly_report | 和顺电气2026年第一季度报告 | company_300141 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300141-chinext-300141-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300141_2025 | annual_report | 和顺电气2025年年度报告 | company_300141 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300141-chinext-300141-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300141_2024 | annual_report | 和顺电气2024年年度报告 | company_300141 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300141-chinext-300141-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300141_2023 | annual_report | 和顺电气2023年年度报告 | company_300141 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300141-chinext-300141-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300144_2026 | quarterly_report | 宋城演艺2026年第一季度报告 | company_300144 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300144-chinext-300144-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300144_2025 | annual_report | 宋城演艺2025年年度报告 | company_300144 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300144-chinext-300144-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300144_2024 | annual_report | 宋城演艺2024年年度报告 | company_300144 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300144-chinext-300144-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300144_2023 | annual_report | 宋城演艺2023年年度报告 | company_300144 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300144-chinext-300144-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300168_2026 | quarterly_report | 万达信息2026年第一季度报告 | company_300168 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300168-chinext-300168-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300168_2025 | annual_report | 万达信息2025年年度报告 | company_300168 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300168-chinext-300168-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300168_2024 | annual_report | 万达信息2024年年度报告 | company_300168 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300168-chinext-300168-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300168_2023 | annual_report | 万达信息2023年年度报告 | company_300168 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300168-chinext-300168-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300169_2026 | quarterly_report | 天晟新材2026年第一季度报告 | company_300169 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300169-chinext-300169-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300169_2025 | annual_report | 天晟新材2025年年度报告 | company_300169 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300169-chinext-300169-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300169_2024 | annual_report | 天晟新材2024年年度报告 | company_300169 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300169-chinext-300169-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300169_2023 | annual_report | 天晟新材2023年年度报告 | company_300169 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300169-chinext-300169-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300181_2026 | quarterly_report | 佐力药业2026年第一季度报告 | company_300181 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300181-chinext-300181-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300181_2025 | annual_report | 佐力药业2025年年度报告 | company_300181 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300181-chinext-300181-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300181_2024 | annual_report | 佐力药业2024年年度报告 | company_300181 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300181-chinext-300181-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300181_2023 | annual_report | 佐力药业2023年年度报告 | company_300181 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300181-chinext-300181-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300187_2026 | quarterly_report | 永清环保2026年第一季度报告 | company_300187 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300187-chinext-300187-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300187_2025 | annual_report | 永清环保2025年年度报告 | company_300187 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300187-chinext-300187-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300187_2024 | annual_report | 永清环保2024年年度报告 | company_300187 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300187-chinext-300187-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300187_2023 | annual_report | 永清环保2023年年度报告 | company_300187 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300187-chinext-300187-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300188_2026 | quarterly_report | 国投智能2026年第一季度报告 | company_300188 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300188-chinext-300188-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300188_2025 | annual_report | 国投智能2025年年度报告 | company_300188 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300188-chinext-300188-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300188_2024 | annual_report | 国投智能2024年年度报告 | company_300188 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300188-chinext-300188-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300188_2023 | annual_report | 国投智能2023年年度报告 | company_300188 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300188-chinext-300188-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300190_2026 | quarterly_report | 维尔利2026年第一季度报告 | company_300190 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300190-chinext-300190-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300190_2025 | annual_report | 维尔利2025年年度报告 | company_300190 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300190-chinext-300190-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300190_2024 | annual_report | 维尔利2024年年度报告 | company_300190 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300190-chinext-300190-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300190_2023 | annual_report | 维尔利2023年年度报告 | company_300190 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300190-chinext-300190-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300193_2026 | quarterly_report | 佳士科技2026年第一季度报告 | company_300193 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300193-chinext-300193-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300193_2025 | annual_report | 佳士科技2025年年度报告 | company_300193 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300193-chinext-300193-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300193_2024 | annual_report | 佳士科技2024年年度报告 | company_300193 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300193-chinext-300193-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300193_2023 | annual_report | 佳士科技2023年年度报告 | company_300193 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300193-chinext-300193-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300194_2026 | quarterly_report | 福安药业2026年第一季度报告 | company_300194 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300194-chinext-300194-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300194_2025 | annual_report | 福安药业2025年年度报告 | company_300194 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300194-chinext-300194-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300194_2024 | annual_report | 福安药业2024年年度报告 | company_300194 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300194-chinext-300194-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300194_2023 | annual_report | 福安药业2023年年度报告 | company_300194 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300194-chinext-300194-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300198_2026 | quarterly_report | *ST纳川2026年第一季度报告 | company_300198 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300198-chinext-300198-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300198_2025 | annual_report | *ST纳川2025年年度报告 | company_300198 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300198-chinext-300198-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300198_2024 | annual_report | *ST纳川2024年年度报告 | company_300198 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300198-chinext-300198-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300198_2023 | annual_report | *ST纳川2023年年度报告 | company_300198 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300198-chinext-300198-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300206_2026 | quarterly_report | 理邦仪器2026年第一季度报告 | company_300206 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300206-chinext-300206-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300206_2025 | annual_report | 理邦仪器2025年年度报告 | company_300206 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300206-chinext-300206-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300206_2024 | annual_report | 理邦仪器2024年年度报告 | company_300206 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300206-chinext-300206-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300206_2023 | annual_report | 理邦仪器2023年年度报告 | company_300206 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300206-chinext-300206-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300207_2026 | quarterly_report | 欣旺达2026年第一季度报告 | company_300207 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300207-chinext-300207-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300207_2025 | annual_report | 欣旺达2025年年度报告 | company_300207 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300207-chinext-300207-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300207_2024 | annual_report | 欣旺达2024年年度报告 | company_300207 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300207-chinext-300207-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300207_2023 | annual_report | 欣旺达2023年年度报告 | company_300207 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300207-chinext-300207-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q_300208_20250630 | quarterly_report | 中程退2025年06月30日报告 | company_300208 | industry_chinext | 2025Q2 |  | 新浪财经公开 API | data/knowledge-base/financials/300208-chinext-300208-financial-2025Q2-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300208_2025 | annual_report | 中程退2025年年度报告 | company_300208 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300208-chinext-300208-financial-2025Q2-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300208_2024 | annual_report | 中程退2024年年度报告 | company_300208 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300208-chinext-300208-financial-2025Q2-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300208_2023 | annual_report | 中程退2023年年度报告 | company_300208 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300208-chinext-300208-financial-2025Q2-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300211_2026 | quarterly_report | *ST亿通2026年第一季度报告 | company_300211 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300211-chinext-300211-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300211_2025 | annual_report | *ST亿通2025年年度报告 | company_300211 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300211-chinext-300211-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300211_2024 | annual_report | *ST亿通2024年年度报告 | company_300211 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300211-chinext-300211-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300211_2023 | annual_report | *ST亿通2023年年度报告 | company_300211 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300211-chinext-300211-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300215_2026 | quarterly_report | 电科院2026年第一季度报告 | company_300215 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300215-chinext-300215-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300215_2025 | annual_report | 电科院2025年年度报告 | company_300215 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300215-chinext-300215-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300215_2024 | annual_report | 电科院2024年年度报告 | company_300215 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300215-chinext-300215-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300215_2023 | annual_report | 电科院2023年年度报告 | company_300215 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300215-chinext-300215-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300228_2026 | quarterly_report | 富瑞特装2026年第一季度报告 | company_300228 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300228-chinext-300228-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300228_2025 | annual_report | 富瑞特装2025年年度报告 | company_300228 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300228-chinext-300228-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300228_2024 | annual_report | 富瑞特装2024年年度报告 | company_300228 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300228-chinext-300228-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300228_2023 | annual_report | 富瑞特装2023年年度报告 | company_300228 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300228-chinext-300228-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300229_2026 | quarterly_report | 拓尔思2026年第一季度报告 | company_300229 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300229-chinext-300229-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300229_2025 | annual_report | 拓尔思2025年年度报告 | company_300229 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300229-chinext-300229-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300229_2024 | annual_report | 拓尔思2024年年度报告 | company_300229 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300229-chinext-300229-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300229_2023 | annual_report | 拓尔思2023年年度报告 | company_300229 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300229-chinext-300229-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300230_2026 | quarterly_report | 永利股份2026年第一季度报告 | company_300230 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300230-chinext-300230-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300230_2025 | annual_report | 永利股份2025年年度报告 | company_300230 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300230-chinext-300230-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300230_2024 | annual_report | 永利股份2024年年度报告 | company_300230 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300230-chinext-300230-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300230_2023 | annual_report | 永利股份2023年年度报告 | company_300230 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300230-chinext-300230-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300233_2026 | quarterly_report | 金城医药2026年第一季度报告 | company_300233 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300233-chinext-300233-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300233_2025 | annual_report | 金城医药2025年年度报告 | company_300233 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300233-chinext-300233-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300233_2024 | annual_report | 金城医药2024年年度报告 | company_300233 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300233-chinext-300233-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300233_2023 | annual_report | 金城医药2023年年度报告 | company_300233 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300233-chinext-300233-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300237_2026 | quarterly_report | ST美晨2026年第一季度报告 | company_300237 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300237-chinext-300237-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300237_2025 | annual_report | ST美晨2025年年度报告 | company_300237 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300237-chinext-300237-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300237_2024 | annual_report | ST美晨2024年年度报告 | company_300237 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300237-chinext-300237-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300237_2023 | annual_report | ST美晨2023年年度报告 | company_300237 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300237-chinext-300237-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300240_2026 | quarterly_report | 飞力达2026年第一季度报告 | company_300240 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300240-chinext-300240-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300240_2025 | annual_report | 飞力达2025年年度报告 | company_300240 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300240-chinext-300240-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300240_2024 | annual_report | 飞力达2024年年度报告 | company_300240 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300240-chinext-300240-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300240_2023 | annual_report | 飞力达2023年年度报告 | company_300240 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300240-chinext-300240-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300252_2026 | quarterly_report | 金信诺2026年第一季度报告 | company_300252 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300252-chinext-300252-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300252_2025 | annual_report | 金信诺2025年年度报告 | company_300252 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300252-chinext-300252-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300252_2024 | annual_report | 金信诺2024年年度报告 | company_300252 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300252-chinext-300252-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300252_2023 | annual_report | 金信诺2023年年度报告 | company_300252 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300252-chinext-300252-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300266_2026 | quarterly_report | 兴源环境2026年第一季度报告 | company_300266 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300266-chinext-300266-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300266_2025 | annual_report | 兴源环境2025年年度报告 | company_300266 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300266-chinext-300266-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300266_2024 | annual_report | 兴源环境2024年年度报告 | company_300266 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300266-chinext-300266-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300266_2023 | annual_report | 兴源环境2023年年度报告 | company_300266 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300266-chinext-300266-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300268_2026 | quarterly_report | 佳沃食品2026年第一季度报告 | company_300268 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300268-chinext-300268-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300268_2025 | annual_report | 佳沃食品2025年年度报告 | company_300268 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300268-chinext-300268-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300268_2024 | annual_report | 佳沃食品2024年年度报告 | company_300268 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300268-chinext-300268-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300268_2023 | annual_report | 佳沃食品2023年年度报告 | company_300268 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300268-chinext-300268-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| q1_300296_2026 | quarterly_report | 利亚德2026年第一季度报告 | company_300296 | industry_chinext | 2026Q1 |  | 新浪财经公开 API | data/knowledge-base/financials/300296-chinext-300296-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300296_2025 | annual_report | 利亚德2025年年度报告 | company_300296 | industry_chinext | 2025A |  | 新浪财经公开 API | data/knowledge-base/financials/300296-chinext-300296-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300296_2024 | annual_report | 利亚德2024年年度报告 | company_300296 | industry_chinext | 2024A |  | 新浪财经公开 API | data/knowledge-base/financials/300296-chinext-300296-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
| ann_300296_2023 | annual_report | 利亚德2023年年度报告 | company_300296 | industry_chinext | 2023A |  | 新浪财经公开 API | data/knowledge-base/financials/300296-chinext-300296-financial-2026Q1-2025A-2024A-2023A.md | false | T-019 新浪财报 API 入库 |
