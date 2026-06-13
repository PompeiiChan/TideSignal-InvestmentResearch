# T-019 知识库扩容入库报告

- 生成时间（UTC）：2026-06-12T14:20:00+00:00
- 随机种子：20260612
- 抽样数量：50
- 成功：50
- 失败：0
- RAG_INDEX_VERSION：已递增至 8（`backend/src/services/rag/chunker.py`）

## 样本 doc_id

- `300007` 汉威科技: ann_300007_2025, q1_300007_2026
- `300014` 亿纬锂能: ann_300014_2025, q1_300014_2026
- `300015` 爱尔眼科: ann_300015_2025, q1_300015_2026
- `300033` 同花顺: ann_300033_2025, q1_300033_2026
- `300023` 宝德退: ann_300023_2025（仅年报，无 2026Q1）

## 检索冒烟（切块）

| 文件 | chunks | 含「营业收入」块 | sample doc_id |
|------|--------|------------------|---------------|
| 300014-chinext-300014-financial-2025A-2026Q1.md | 4 | 2 | ann_300014_2025 |
| 300033-chinext-300033-financial-2025A-2026Q1.md | 4 | 2 | ann_300033_2025 |
| 300015-chinext-300015-financial-2025A-2026Q1.md | 4 | 2 | ann_300015_2025 |

## pytest 摘要

`backend/tests/test_rag_service.py`：16 passed, 6 skipped（含 `test_count_markdown_files_matches_repository` 已更新为 86）。

## 索引说明

未执行全量 embedding（`.index/` 在 gitignore）。**需重启后端**以触发 RAG_INDEX_VERSION=8 全量索引重建。
