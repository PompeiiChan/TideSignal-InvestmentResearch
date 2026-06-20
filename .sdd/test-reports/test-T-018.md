# 测试报告：T-018 问股 live 基本面 Tool（新浪/同花顺/东财/巨潮）

**测试时间**：2026-06-20  
**Tester Agent ID**：cursor-tester

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户在客户端询问知识库未收录的 A 股（如创业板随机公司）基本面，回答能引用新浪财务关键指标（营收、净利润、毛利率、ROE 等）并标明报告期 | **PASS** | REAL_API 冒烟：`lookup_financial_profile(stock_code=301001.SZ)` → `found=True`、`data_origin=sina_api`、`fallback_used=False`、3 期数据。联调 POST `/api/chat/query`「301001.SZ 凯淳股份基本面怎么样」→ 首轮 `tool_call` 中 `mock_financial_profile_lookup` 为 `sina_api` live，回答含 2024–2026Q1 财务与报告期表述 |
| 2 | 问「机构怎么看某某公司」时，能展示同花顺一致预期或东财研报列表元数据（评级、EPS 预测等），非空答 | **PASS** | 联调「机构怎么看宁德时代」→ `tool_call` 含 `consensus_valuation_lookup`（`data_origin=ths_worth_consensus`、`fallback_used=False`）与 `research_report_metadata_lookup`（`eastmoney_reportapi`、20 条研报）。助手回答 2834 字，含机构态度与评级/EPS 口径，非空 |
| 3 | 问股 Trace 的 tool_call 节点可见各 Tool 名称、is_mock/fallback 状态与数据来源归因（含 third_party/a-stock-data Apache-2.0） | **PASS** | GET `/api/traces/trace_20260620_111136_001_local` → `tool_call.output.tool_attributions` 3 条，均含 `attribution=third_party/a-stock-data (Apache-2.0)`；`detail_sections` 含「工具归因」及 origin/mock/fallback 摘要 |
| 4 | 外部接口失败时回答不 500，降级为本地 KB 或明确说明暂无结构化数据；不得把 live 失败伪装成真实 PASS | **PASS** | 单测 `test_lookup_research_report_metadata_fallback_on_empty`、`test_lookup_not_found_when_all_sources_empty` 等覆盖 fallback。联调宁德时代财务 Tool 为 `local_profile_cache` + `fallback_used=True`，Trace 明确标注，未伪装 live。HTTP 200，无 500 |
| 5 | 问股 Prompt 边界不变：不接 K 线/盘口/短线资金流；估值仅 PE/PB 等基本面口径 | **PASS** | 代码审查：`stock_tool_plan` 机构/综合编排仅含 financial/consensus/report/valuation Tool；未新增 K 线/盘口 Tool。本任务未改 PRD 边界 Prompt 约束 |

## technicalChecks

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | T-018 相关 pytest | **PASS** | 默认：34 passed, 2 skipped；`REAL_API_TEST=1` 研报 2 passed（见命令摘要） |
| 2 | 新浪/东财客户端 trust_env=False | **PASS** | `eastmoney_client.py:29`、sina_finance_client 均设 `trust_env=False` |
| 3 | research_report_metadata_lookup 注册 + 机构编排 | **PASS** | `test_resolve_stock_tool_names_institution_view`；Trace 联调含三 Tool |
| 4 | tool_call Trace 归因字段 | **PASS** | `test_tool_call_uses_agent_tool_names_for_stock_route` + 联调 `tool_attributions` |
| 5 | GET /api/data-sources/status live 条目 | **PASS** | `test_data_sources_status_contract`；curl 实测含 `financial_live/consensus_live/report_live/announcement_live` |
| 6 | REAL_API_TEST 冒烟（Sina / THS / 东财研报） | **PASS** | ① 301001 Sina live ② `lookup_consensus_valuation_tool(600519.SH)` → `ths_worth_consensus` ③ 东财研报 pytest real 2/2 |
| 7 | frontend type-check | **PASS** | `npm run type-check` 退出码 0（Developer 已声明；Tester 复跑通过） |
| 8 | VITE_USE_MOCK=false 问股经 LangGraph tool_call 命中真实后端 | **PASS** | 8099 后端 curl 联调两条问股 Query，Trace 含 live/fallback 边界 |

## 命令执行摘要

### pytest（默认，无 REAL_API_TEST）

```bash
cd Projects_Repo/smart-investment-research
PYTHONPATH=.:backend .venv/bin/python -m pytest \
  backend/tests/test_financial_profile_lookup.py \
  backend/tests/test_consensus_valuation.py \
  backend/tests/test_research_report_metadata_lookup.py \
  backend/tests/test_stock_tool_plan.py \
  backend/tests/test_tool_call_stock_plan.py \
  backend/tests/test_stock_evidence_api_lookup.py \
  backend/tests/test_health.py -v
```

```text
34 passed, 2 skipped in 1.04s
```

### REAL_API_TEST（东财研报）

```bash
REAL_API_TEST=1 PYTHONPATH=.:backend .venv/bin/python -m pytest \
  backend/tests/test_research_report_metadata_lookup.py -k real -v
```

```text
2 passed in 4.40s
```

### REAL_API 手工冒烟（Sina + THS consensus tool）

| ID | 输入 | 结果 |
|----|------|------|
| RT-018-01 | `lookup_financial_profile(301001.SZ)` | `data_origin=sina_api`, `fallback_used=False`, 3 periods |
| RT-018-02 | `lookup_consensus_valuation_tool(600519.SH)` | `found=True`, `data_origin=ths_worth_consensus`, bear/base/bull |
| RT-018-03 | `lookup_research_report_metadata(600519.SH)` | `found=True`, 20 reports, rating 买入 |

### 后端联调（8099）

```bash
# 机构观点
POST /api/chat/query {"session_id":"…","source":"client","query":"机构怎么看宁德时代"}
→ trace_20260620_111136_001_local：tool_call 含 financial(KB fallback) + consensus(THS live) + report(EM live)

# 未收录创业板基本面
POST /api/chat/query {"query":"301001.SZ 凯淳股份基本面怎么样"}
→ trace_20260620_111424_003_local：首轮 tool_call financial sina_api live
```

### ruff（T-018 核心文件抽检）

```text
All checks passed!
```

## 代码审查要点

| 要点 | 结果 | 位置 |
|------|------|------|
| 东财研报元数据 Tool | **PASS** | `em_research_report_client.py`、`research_report_metadata_lookup.py` |
| 机构类 stock_tool_plan 编排 | **PASS** | `stock_tool_plan.py` `_INSTITUTION_VIEW_RE` |
| eastmoney trust_env=False | **PASS** | `eastmoney_client.py:29` |
| live 数据源 status | **PASS** | `config_status_service.py` + `test_health.py` |
| 密钥泄露 | **PASS** | T-018 变更文件与 completion 报告无真实 Key |
| TODO/FIXME | **PASS** | 新增文件无遗留标记 |

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|-------------|
| 1 | 全量 `ruff`/`mypy` 仍有仓库既有问题（response_assembly E402 等） | 历史债务 | Developer 已在 completion 说明；T-018 核心文件 ruff 通过 |
| 2 | `lookup_consensus_valuation()` 直接传 `600519.SH` 不走 `resolve_stock_code` 会失败；经 Tool 包装正常 | consensus_valuation | 可选在 service 层统一 normalize；非 T-018 blocker |
| 3 | 宁德时代已在 KB，`mock_financial_profile_lookup` 机构问句走 `local_profile_cache` fallback，Trace 已正确标注 | 预期行为 | 用户门禁可另选 KB 外代码验证 Sina live 路径 |

---

**技术验收结论**：T-018 满足 acceptanceCriteria 与 technicalChecks。live Tool、Trace 归因、数据源 status 与 fallback 边界均已独立验证。用户门禁见 `.sdd/test-reports/acceptance-roadmap-T-018.md`。
