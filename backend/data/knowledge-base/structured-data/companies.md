# 结构化数据：companies

> 迁移说明：本文由现有知识库资料转换为 Markdown，用于智能投研 demo、RAG 检索、结构化证据追溯和评测。本文不构成投资建议。

## 迁移元数据

| 字段 | 内容 |
|---|---|
| 资料类型 | structured_csv |
| 原始路径 | data/metadata/companies.csv |
| 迁移后目录 | structured-data |
| 迁移文件 | companies.md |

## 数据表说明

- 原始路径：`data/metadata/companies.csv`
- 字段数量：7
- 数据行数：55
- mock 标记统计：该表无 `is_mock` 字段，请结合表名、字段和备注判断用途。

## 字段

| 序号 | 字段名 |
|---:|---|
| 1 | `company_id` |
| 2 | `company_name` |
| 3 | `ticker` |
| 4 | `exchange` |
| 5 | `industry_id` |
| 6 | `market` |
| 7 | `business_summary` |

## 数据

| company_id | company_name | ticker | exchange | industry_id | market | business_summary |
| --- | --- | --- | --- | --- | --- | --- |
| company_000568 | 泸州老窖 | 000568.SZ | SZSE | industry_baijiu | A股 | 白酒生产和销售企业 |
| company_603288 | 海天味业 | 603288.SH | SSE | industry_condiment | A股 | 调味品生产和销售企业 |
| company_688256 | 寒武纪 | 688256.SH | SSE_STAR | industry_chip | A股 | AI芯片和智能计算相关企业 |
| company_002293 | 罗莱生活 | 002293.SZ | SZSE | industry_textile | A股 | 家用纺织品和家居生活消费品企业 |
| company_300750 | 宁德时代 | 300750.SZ | SZSE_CHINEXT | industry_new_energy_battery | A股 | 动力电池和储能电池企业 |

---
免责声明：本文仅用于智能投研系统知识库迁移与测试，不构成投资建议。投资有风险，入市需谨慎。

| company_300007 | 汉威科技 | 300007.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300014 | 亿纬锂能 | 300014.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300015 | 爱尔眼科 | 300015.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300019 | 硅宝科技 | 300019.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300023 | 宝德退 | 300023.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300030 | 阳普医疗 | 300030.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300033 | 同花顺 | 300033.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300048 | 合康新能 | 300048.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300053 | 航宇微 | 300053.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300057 | 万顺新材 | 300057.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300061 | 旗天科技 | 300061.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300074 | 华平股份 | 300074.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300076 | *ST宁视 | 300076.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300077 | 国民技术 | 300077.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300085 | 银之杰 | 300085.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300090 | 盛运退 | 300090.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300092 | 科新机电 | 300092.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300104 | 乐视退 | 300104.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300105 | 龙源技术 | 300105.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300109 | 新开源 | 300109.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300113 | 顺网科技 | 300113.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300119 | 瑞普生物 | 300119.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300128 | 锦富技术 | 300128.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300129 | 泰胜风能 | 300129.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300141 | 和顺电气 | 300141.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300144 | 宋城演艺 | 300144.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300168 | 万达信息 | 300168.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300169 | 天晟新材 | 300169.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300181 | 佐力药业 | 300181.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300187 | 永清环保 | 300187.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300188 | 国投智能 | 300188.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300190 | 维尔利 | 300190.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300193 | 佳士科技 | 300193.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300194 | 福安药业 | 300194.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300198 | *ST纳川 | 300198.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300206 | 理邦仪器 | 300206.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300207 | 欣旺达 | 300207.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300208 | 中程退 | 300208.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300211 | *ST亿通 | 300211.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300215 | 电科院 | 300215.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300228 | 富瑞特装 | 300228.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300229 | 拓尔思 | 300229.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300230 | 永利股份 | 300230.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300233 | 金城医药 | 300233.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300237 | ST美晨 | 300237.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300240 | 飞力达 | 300240.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300252 | 金信诺 | 300252.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300266 | 兴源环境 | 300266.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300268 | 佳沃食品 | 300268.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |
| company_300296 | 利亚德 | 300296.SZ | SZSE_CHINEXT | industry_chinext | A股 | 创业板上市公司，新浪财经财报 API 入库（T-019） |