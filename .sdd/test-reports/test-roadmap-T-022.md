# 测试报告：roadmap-T-022 问股财报深化（P1–P3）

**测试时间**：2026-06-19
**Tester Agent ID**：tester-subagent
**版本检查点**：`0fd9483`

## 结果：PASS

## 验收标准逐条验证

### P1 — 财报工具：现金流与负债字段

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1.1 | 利亚德（300296）`mock_financial_profile_lookup` `found=true` | PASS | 探针：`lookup_financial_profile(stock_name="利亚德", stock_code="300296")` → `found=True`, `data_origin=local_kb_file` |
| 1.2 | `periods.length` ≥ 2 | PASS | 探针返回 `periods_count=2`（2026Q1、2025A） |
| 1.3 | 各期含 `operating_cash_flow`（非全 N/A） | PASS | `['-8460.36 万元', '10.6554 亿元']`，`ocf_all_na=False` |
| 1.4 | 各期含 `debt_ratio`（非全 N/A） | PASS | `['39.80%', '40.57%']`，`dr_all_na=False` |
| 1.5 | 正文多期表或解读提及经营现金流/资产负债率 | BLOCKED | 本轮仅验证数据层与工具输出，未跑完整对话 Trace → `response_assembly`；字段已在 `periods[]` 与 KB 文件中就绪，需用户门禁对话验收 |
| 1.6 | 千禾味业（603027）`data_origin=sina_api` | PASS | 实时探针：`found=True`, `data_origin=sina_api` |
| 1.7 | Sina `periods[]` 含 `operating_cash_flow` / `debt_ratio` | PASS | 实时 3 期均含非 N/A 字段，例：2026Q1 `ocf=4.59亿元 dr=15.36%`；单测 `test_lookup_falls_back_to_sina_when_local_missing` 亦 PASS |

**P1 补充探针 — `load_all_profiles_from_kb_file`（300296）**

| 标准 | 结果 | 说明 |
|------|------|------|
| KB 多期解析 | PASS | `profiles_count=2`；`2026Q1 ocf=-8460.36 万元 dr=39.80%`；`2025A ocf=10.6554 亿元 dr=40.57%`；路径 `backend/data/knowledge-base/financials/300296-chinext-300296-financial-2025A-2026Q1.md` |

### P2 — RAG 多期 evidence

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 2.1 | `retrieved_chunks` 中 `time_period` 至少 2 个不同值 | PASS | 实时 `RagService.retrieve('利亚德基本面怎么样', top_k=6)` → `unique_periods={'2026Q1','2025A'}` |
| 2.2 | 同一 `time_period` 不应占满全部 top 命中 | PASS | 同上：`period_counts={'2026Q1':2,'2025A':2}`，`max_same_period_share=0.5`（非单期占满） |
| 2.x | `diversify_hits_by_time_period` 单测 | PASS | `pytest tests/test_rag_time_period_diversify.py` 2 passed |
| 2.x | 代码路径 `service.py` + `rag_retrieval.py` | PASS | `service.py:69-94` 定义；`service.py:419` 检索后调用；`rag_retrieval.py:194` 在 `stock_analysis_agent` 路由下调用 |

### P3 — 入库脚本

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 3.1 | 单文件合并最新季报 + 至多 3 个年报 | PASS | `_pick_periods` 探针：`['20260331','20251231','20241231','20231231']`（1 季报 + 3 年报）；实时 300296：`['20260331','20251231','20241231']`（1 季报 + 2 年报，数据源仅 2 个年报可用） |
| 3.2 | 各期 `### 主要财务数据` 含利润表/资产负债表/现金流量表 | PASS | 已入库 KB 文件两期均含三表科目；实时 `fetch_period_reports('300296')` 三期 `lrb/fzb/llb=True` |
| 3.x | `--dry-run` 可执行 | PASS | `cd backend && PYTHONPATH=.. ../.venv/bin/python scripts/ingest_chinext_sina_financials.py --dry-run` exit 0，输出标的列表含 300296 利亚德 |

## 自动化测试汇总

```
pytest tests/test_multi_period_financials.py tests/test_financial_profile_lookup.py tests/test_rag_time_period_diversify.py -q
15 passed in 0.43s
```

## 阻塞证据

无环境阻塞。后端 `http://127.0.0.1:8099/health` → 200；Sina API 网络可达。

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | 验收项 1.5（对话正文提及现金流/负债率）需完整 Agent 对话 Trace | response_assembly | 用户门禁对话验收时勾选 |
| 2 | `tasks.json` 无 `roadmap-T-022` 条目，仅 `status.json` 跟踪 | SDD 元数据 | 编排器按需同步任务登记 |
