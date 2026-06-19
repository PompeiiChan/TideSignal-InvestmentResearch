# 用户验收清单：路线图 T-022-P1 问股财报深化

**版本检查点**：`c6c5eba` 及之后 T-022 开发提交  
**验收环境**：`VITE_USE_MOCK=false` · 后端 **8099** · 前端 **5199**

---

## 1. 财报工具：现金流与负债字段

**提问（已入库创业板标的）**：

> 利亚德基本面怎么样？

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 1.1 | 工具命中 | Trace `mock_financial_profile_lookup` `found=true` | |
| 1.2 | 多期 | `periods.length` ≥ 2 | |
| 1.3 | 现金流 | 各期含 `operating_cash_flow`（非全 N/A） | |
| 1.4 | 负债率 | 各期含 `debt_ratio`（非全 N/A） | |
| 1.5 | 正文 | 多期表或解读提及经营现金流/资产负债率（有数据时） | |

**提问（仅 Sina API 标的，如千禾味业）**：

> 千禾味业财报怎么样？

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 1.6 | 数据源 | `data_origin=sina_api` | |
| 1.7 | 扩展字段 | Trace `periods[]` 含 `operating_cash_flow` / `debt_ratio` | |

---

## 2. RAG 多期 evidence（P2）

对已入库多期财报标的提问综合基本面，Trace → `rag_retrieval`：

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 2.1 | 多期片段 | `retrieved_chunks` 中 `time_period` **至少 2 个不同值**（如 2026Q1 + 2025A） | |
| 2.2 | 非重复堆砌 | 同一 `time_period` 不应占满全部 top 命中 | |

---

## 3. 入库脚本（P3，可选重跑）

```bash
cd backend && PYTHONPATH=.. python scripts/ingest_chinext_sina_financials.py --dry-run
```

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 3.1 | 期数 | 单文件合并 **最新季报 + 至多 3 个年报** 段落 | |
| 3.2 | 三表 | 各期 `### 主要财务数据` 含利润表/资产负债表/现金流量表科目 | |

---

**全部通过后请回复**：「财报 P1 验收通过」（或按实际完成的子阶段说明）。

**✅ 用户已于 2026-06-19 确认通过**（见 `acceptance-roadmap-T-022-P1-result.md`）。

**T-022 backlog（不阻塞 T-023）**：P3 批量重跑 ingest 扩 KB 至 3 年报。
