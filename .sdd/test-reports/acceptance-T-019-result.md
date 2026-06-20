# 用户验收结果：T-019 知识库扩容（创业板 50 家财报）

**验收日期**：2026-06-20  
**验收人**：用户  
**结论**：**PASS**

## 验收范围

- `financials/` 新增 50 家创业板新浪三表 Markdown；`companies.md` / `document_manifest.md` 同步
- RAG 索引重建后，问股可命中新增公司财报片段（营业收入/净利润等可检索）
- 与 **T-024** 批量 refresh（3 年报 + 最新季报）叠加后 KB 覆盖约 55 家标的

## 交付物

- 入库报告：`.sdd/test-reports/T-019-ingestion-report.md`（50/50 成功，seed 20260612）
- 批量脚本：`backend/scripts/ingest_chinext_sina_financials.py`（T-024 `--refresh` 复用）

## 代码基线

- 功能检查点：`0d092de`（含 T-024 KB 扩容与 assembly 优化同批推送）

## 后续

- 运营向：头部标的（如恒瑞）`company-reports/` 深度研报入库见 `response-bad-case.md` BC-006
