# 智能投研知识库

> **扩容操作手册**（raw → Markdown → 元数据 → 切块 → 索引）：[`docs/knowledge-base-ingestion.md`](../../../docs/knowledge-base-ingestion.md)  
> 新增或批量导入资料时，必须先读该文档，再落盘本目录。

本目录为 V1.1 RAG / hotspot_agent / 问股 / 问行业 / 问数 的本地 Markdown 知识库。路径相对于项目根：

`Projects_Repo/smart-investment-research/backend/data/knowledge-base/`

在 `backend/.env` 中配置：

```env
LOCAL_KB_PATH=data/knowledge-base
```

## 目录结构（当前已就位）

| 目录 | 文件数 | 内容 | 状态 |
|------|--------|------|------|
| `hotspots/` | 3 | A 股月度市场热点（2026 年 4 / 5 / 6 月） | ✅ 已就位 |
| `financials/` | 55 | 5 家样本 + 50 家创业板新浪 API 财报（2025A + 2026Q1 合并） | ✅ 已就位 |
| `company-reports/` | 5 | 5 家样本公司研报 | ✅ 已就位 |
| `industry-reports/` | 10 | 行业研报（白酒、调味品、芯片、纺织、新能源电池、保险、建材、机械、家电等） | ✅ 已就位 |
| `structured-data/` | 13 | 文档清单、公司/行业表、问数用 mock 结构化数据 | ✅ 已就位 |

**合计**：86 个可索引 Markdown 文件（`list_markdown_files` 计数，不含各目录 `README.md`）。

## 热点文档原则

`hotspots/` **只描述市场热点本身**（主题、政策、板块、事件、归因），**不要求**与 `financials/`、`company-reports/` 中的样本公司或行业一一对应。文中出现的个股仅来自公开报道案例，不代表固定股票池。

| 文件 | 时间口径 | 说明 |
|------|----------|------|
| `2026-04-market-hotspots.md` | 2026 年 4 月完整月 | 早期迁移版，含部分 demo 样本映射 |
| `2026-05-market-hotspots.md` | 2026-05-01～2026-05-29 | 完整 5 月收官复盘，`is_mock=false` |
| `2026-06-market-hotspots.md` | 2026-06-01～2026-06-11 | **阶段性**月报（6 月未结束），`is_mock=false` |

## 命名规范摘要

| 子目录 | 命名模式 | 示例 |
|--------|----------|------|
| `hotspots/` | `YYYY-MM-market-hotspots.md` | `2026-05-market-hotspots.md` |
| `financials/` | `{code}-{slug}-financial-2025A-2026Q1.md` | `300750-ningdeshidai-financial-2025A-2026Q1.md` |
| `company-reports/` | `{code}-{slug}-company-report-2026.md` | `300750-ningdeshidai-company-report-2026.md` |
| `industry-reports/` | `{industry}-industry-report-{period}.md` | `baijiu-industry-report-2026.md` |

## 五家样本公司（财报 / 公司研报）

| 代码 | 公司 | 行业 |
|------|------|------|
| 000568 | 泸州老窖 | 白酒 |
| 002293 | 罗莱生活 | 家纺纺织 |
| 300750 | 宁德时代 | 新能源电池 |
| 603288 | 海天味业 | 调味品 |
| 688256 | 寒武纪 | AI 芯片 |

## 索引与清单

- 全库文档登记：`structured-data/document_manifest.md`（122 条 `is_mock=false` 文档记录）
- 公司表：`structured-data/companies.md`（55 家公司，含 T-019 创业板批次 50 家）
- 创业板批次清单：`structured-data/companies_chinext_batch1.json`
- 行业表：`structured-data/industries.md`

## Mock 数据警示

`structured-data/` 中带 `is_mock=true` 或文件名含 `mock` 的表仅用于问数 demo，不代表真实行情事实。Agent 回答用户时应优先 `is_mock=false` 且有来源的条目。

## 与 `backend/data/mock/` 的边界

- **`knowledge-base/`**：RAG 非结构化/半结构化 Markdown（热点、财报、研报、清单）
- **`mock/`**（`MOCK_DATA_PATH`）：问数工具用的结构化 Mock 行情/财务数据

二者不要混放。

## 合规说明

本目录仅用于智能投研系统知识库、检索测试和 demo 验证，不构成投资建议。
