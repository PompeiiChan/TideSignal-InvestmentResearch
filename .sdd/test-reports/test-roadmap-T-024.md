# 测试报告：roadmap-T-024 离线 KB 与入库扩展

**测试时间**：2026-06-19  
**Tester Agent ID**：主会话自动化  
**版本检查点**：`ac6dc6a`

## 结果：PASS

## 验收标准逐条验证

### P1 — 入库脚本与批量刷新

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1.1 | `--refresh` 从 delivery JSON 重跑 | PASS | `ingest_chinext_sina_financials.py --refresh` |
| 1.2 | 旧 financials 文件清理 | PASS | 文件名随期数标签变化时删除同 code 旧文件 |
| 1.3 | manifest 行替换 | PASS | refresh 模式按 code 移除旧 `ann_/q1_/q_` 行后写入 |
| 1.4 | `--codes` 不缩 delivery JSON | PASS | `merge=True` 修复局部刷新覆盖全量列表问题 |
| 1.5 | Sina 拉取深度 | PASS | `SINA_REPORT_NUM=12` |

### P2 — KB 文件期数

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 2.1 | 批量 50 标的成功 | PASS | `T-024-ingestion-report.md` success=50 fail=0 |
| 2.2 | 抽样 4 段（1 季报 + 3 年报） | PASS | 50/50 创业板样本 `sections=4 annual=3 interim=1` |
| 2.3 | 利亚德 300296 | PASS | `profiles=4`；`2026Q1-2025A-2024A-2023A` |
| 2.4 | 例外 300750 | N/A | `EXCLUDE_CODES` 未纳入 batch，保留旧 2 期文件 |

### P3 — 问股多期 loader

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 3.1 | `load_all_profiles_from_kb_file` 多期 | PASS | 300296 → 4 profiles |
| 3.2 | `pick_financial_periods` 单测 | PASS | `test_financial_ingest.py` |

## 自动化测试汇总

```
cd backend && PYTHONPATH=.. ../.venv/bin/python -m pytest \
  tests/test_financial_ingest.py \
  tests/test_multi_period_financials.py \
  tests/test_financial_profile_lookup.py -q
16 passed
```

## 阻塞证据

无。完整对话 Trace（问股多期 RAG）需用户门禁。

## 超出范围

| # | 问题 | 建议 |
|---|------|------|
| 1 | 300750 宁德时代旧文件未刷新 | 非 batch 样本；可手动 `--refresh --codes 300750` 或删除 |
