# T-018 完成报告 — 问股 live 基本面 Tool

> **任务 ID**：T-018  
> **完成日期**：2026-06-20  
> **状态**：`testing`（待 Tester 联调）

---

## 1. 实现摘要

按 `.sdd/developer-reports/T-018-plan.md` S1→S9 完成：

| 步骤 | 内容 | 状态 |
|------|------|------|
| S1 | `em_research_report_client.py` + HTTP mock 单测 | ✅ |
| S2 | `research_report_metadata_lookup` Tool + `TOOL_REGISTRY` | ✅ |
| S3 | `stock_tool_plan` 机构类编排 + 白名单 + 单测 | ✅ |
| S4 | `stock_analysis` / `assembly` Prompt + `citation_catalog` | ✅ |
| S5 | `tool_call` Trace `detail_sections` + `tool_attributions` | ✅ |
| S6 | `config_status_service` live 数据源条目 | ✅ |
| S7 | `eastmoney_client.trust_env=False` | ✅ |
| S8 | 单测 + `REAL_API_TEST` 可选冒烟 | ✅ |
| S9 | 前端 `SourceType` 扩展；`VITE_USE_MOCK=false` 路径无新增 Mock | ✅（浏览器联调交 Tester） |

---

## 2. 变更文件

### 新建
- `backend/src/integrations/market_data/em_research_report_client.py`
- `backend/src/agents/tools/research_report_metadata_lookup.py`
- `backend/tests/test_research_report_metadata_lookup.py`

### 修改
- `backend/src/integrations/market_data/em_report_consensus_client.py` — 复用共享列表 fetch
- `backend/src/integrations/market_data/eastmoney_client.py` — `trust_env=False`
- `backend/src/agents/stock_tool_plan.py` — 机构类编排 + 白名单
- `backend/src/agents/tools/__init__.py` — 注册新 Tool
- `backend/src/agents/tools/mock_financial_profile_lookup.py` — attribution/fallback 字段
- `backend/src/agents/nodes/tool_call.py` — Trace 归因
- `backend/src/services/consensus_valuation.py` — 统一 Tool 契约字段
- `backend/src/services/config_status_service.py` — live 数据源可观测
- `backend/src/services/citation_catalog.py` — consensus / 研报元数据引用
- `backend/src/services/evidence_gaps.py` — `institution_view_thin` 补数
- `backend/src/models/config_status.py` — `SourceType` 扩展
- `backend/src/integrations/llm/prompts/agents/stock_analysis.py`
- `backend/src/integrations/llm/prompts/assembly.py`
- `backend/tests/test_stock_tool_plan.py`
- `backend/tests/test_tool_call_stock_plan.py`
- `backend/tests/test_health.py`
- `frontend/src/types/api.ts` — `SourceType` 对齐后端

---

## 3. 质量门禁

```text
PYTHONPATH=.:backend pytest（T-018 相关）：
  31 passed, 2 skipped（REAL_API_TEST 未设置）

ruff（全量 backend/src backend/tests）：
  2 个既有错误（response_assembly.py E402，非本任务引入）

mypy（全量 backend/src backend/tests）：
  8 个既有错误（financial_ingest / response_assembly / rag_retrieval_query，非本任务引入）

mypy（本任务新增/核心改动文件）：通过

frontend npm run type-check：通过
```

### REAL_API_TEST 用例（需 Tester 授权网络）

```bash
REAL_API_TEST=1 PYTHONPATH=.:backend $PY -m pytest \
  backend/tests/test_research_report_metadata_lookup.py -k real -v
```

---

## 4. Tester 验收要点

1. **机构怎么看**：问「机构怎么看宁德时代」→ `tool_call` 含 `consensus_valuation_lookup` + `research_report_metadata_lookup`；Trace 见 `data_origin` / `fallback` / Apache-2.0 归因。
2. **未收录创业板基本面**：选 KB 外代码 → 新浪 `data_origin=sina_api` 或 KB fallback，不得空编。
3. **GET /api/data-sources/status**：可见 `financial_live` / `consensus_live` / `report_live` / `announcement_live`。
4. **VITE_USE_MOCK=false**：`POST /api/chat/query` 经 8099；管理端 Trace 无 Mock 残留。
5. **fallback 边界**：断网/mock 5xx 单测已覆盖 `fallback_used=true`；真实验收不得把 fallback 标 live PASS。

---

## 5. 已知限制

- 东财 reportapi 启动探针（plan P2 可选）未实现；status 固定 `ready`，失败时由 Tool 层降级。
- `mock_financial_profile_lookup` registry 键名未改（兼容既有图与测试）。
- iwencai NL 研报搜索、PDF 入库不在本任务范围。
- 全量 `ruff`/`mypy` 仍有仓库既有问题，本任务改动文件已单独验证。

---

## 6. 密钥说明

所有 live 数据源为零 key 公开 HTTP；status API 不返回密钥字段。
