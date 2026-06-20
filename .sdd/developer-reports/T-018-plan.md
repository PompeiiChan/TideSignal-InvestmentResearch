# T-018 问股 live 基本面 Tool（新浪/同花顺/东财/巨潮）— 技术方案

> **任务 ID**：T-018  
> **source_feature**：F21 / 问股 live 数据  
> **依据文档**：`docs/PRD.md` §8.4、`docs/api-contracts.md`、`third_party/a-stock-data/SKILL.md`、`.sdd/tasks.json`  
> **前置**：T-013 ✅（V1.1 真实 AI 全链路）、T-012 ✅（LangGraph）、路线图 T-020～T-024 ✅  
> **产出日期**：2026-06-20  
> **状态**：待 Developer 执行（方案就绪）

---

## 1. 背景与目标

### 1.1 产品目标

问股链路在本地 RAG（`financials/`、研报 Markdown）之外，**默认**通过公开 HTTP API 为任意 A 股补齐：

| # | 能力 | 数据源 | 与 RAG 分工 |
|---|------|--------|-------------|
| ① | 财报三表财务快照（多期） | 新浪财经 `CompanyFinanceService.getFinanceReport2022` | Tool 补结构化数字；RAG 保留全文解读 |
| ② | 机构一致预期（EPS×PE 情景） | 同花顺 `worth.html` | Tool 补共识数字；RAG 补观点叙述 |
| ③ | 研报列表元数据 | 东财 `reportapi.eastmoney.com/report/list` | Tool 补评级/EPS 列表；RAG 补 PDF 深度 |
| ④ | 公告 + 快讯事实层 | 巨潮 `cninfo` + 东财全球资讯 | 补数/未收录标的；不替代财报数字 |
| ⑤ | 实时估值（可选） | 腾讯 `qt.gtimg.cn` + 东财历史分位 | 已在 T-021 落地 |

失败时：**本地 KB → 明确缺失说明**，Trace 标明 `data_origin` / `fallback_used`，**不得把 fallback 判为 live PASS**。

### 1.2 非目标

- K 线/盘口/短线资金流/技术指标（PRD §8.4 边界不变）
- iwencai NL 研报搜索、PDF 下载与入库（留给后续 KB 扩容 / T-019 类任务）
- 重命名 registry 键 `mock_financial_profile_lookup`（保持兼容，仅在 Trace/UI 展示层补充别名说明）
- 修改 T-019 知识库 ingest 脚本路径

---

## 2. 差距分析（Orchestrator 探查 + Planner 验证）

### 2.1 已有基础设施（**勿从零设计**）

| 层级 | 路径 | 现状 |
|------|------|------|
| 新浪三表 | `integrations/market_data/sina_finance_client.py` | ✅ `fetch_multi_period_profiles`、节流 ≥1s、`trust_env=False` |
| 同花顺一致预期 | `integrations/market_data/ths_worth_client.py` | ✅ HTML 解析 EPS + 动态 PE |
| 东财研报 EPS 聚合 | `integrations/market_data/em_report_consensus_client.py` | ✅ `fetch_em_report_consensus`（聚合用，**非列表元数据 Tool**） |
| 东财通用 HTTP | `integrations/market_data/eastmoney_client.py` | ✅ `em_get` 限流；⚠️ `requests.Session` **未**显式 `trust_env=False` |
| 巨潮公告 | `integrations/market_data/cninfo_client.py` | ✅ |
| 东财快讯 | `integrations/market_data/news_client.py` | ✅ |
| 腾讯估值 | `integrations/market_data/tencent_quote_client.py` | ✅ T-021 已接入 |
| 财务 Tool | `agents/tools/mock_financial_profile_lookup.py` | ✅ 内置样本 → KB → **新浪 live** 三级 fallback |
| 一致预期 Tool | `agents/tools/consensus_valuation_lookup.py` + `services/consensus_valuation.py` | ✅ THS → 东财 EPS 聚合 → KB fallback |
| 公告/快讯 Tool | `agents/tools/stock_evidence_api_lookup.py` | ✅ 仅 **evidence_gap 补数** 默认触发 |
| 估值 Tool | `agents/tools/valuation_profile_lookup.py` | ✅ |
| 动态编排 | `agents/stock_tool_plan.py` | ✅ 白名单含 5 工具；默认仅 `mock_financial` [+ `valuation`] |
| 节点 | `nodes/stock_analysis_agent.py`、`nodes/tool_call.py` | ✅ 已接 `resolve_stock_tool_names` |
| 单测 | `test_financial_profile_lookup.py`、`test_consensus_valuation.py`、`test_stock_evidence_api_lookup.py`、`test_stock_tool_plan.py`、`test_tool_call_stock_plan.py` | ✅ 局部覆盖 |

### 2.2 关键差距（T-018 须补齐）

| # | 差距 | 影响 | 优先级 |
|---|------|------|--------|
| G1 | **缺独立「东财研报元数据」Tool**（③） | 「机构怎么看」无法展示研报列表（标题/机构/评级/EPS），仅有共识聚合 | P0 |
| G2 | **`consensus_valuation_lookup` 未进入问股默认编排** | 「机构怎么看」依赖 RAG 或 scenario_return；AC 要求 THS/东财 live | P0 |
| G3 | **`stock_analysis` Prompt 白名单仅 2 工具** | LLM 不会规划 consensus / 研报元数据 / 公告 API | P0 |
| G4 | **`tool_call` Trace 缺统一归因字段** | AC 要求可见 tool 名、`is_mock`/`fallback`、`third_party/a-stock-data` 归因 | P0 |
| G5 | **`GET /api/data-sources/status` 未区分 live API** | 财务仍展示 KB 路径；新浪/THS/东财 live 不可观测 | P1 |
| G6 | **`eastmoney_client` 未 `trust_env=False`** | 违反系统级经验，代理环境可能误路由 | P1 |
| G7 | **缺问股 live 端到端验收用例** | Tester 可能只用 mock HTTP 或 KB 样本判 PASS | P0 |
| G8 | **`tasks.json` 顶层 external_services 仍写「MVP 不接入」** | 与 T-018 矛盾，Tester 口径混乱 | P2（Planner 同步） |

### 2.3 已满足、仅需串联/验收的能力

- ① 新浪财报：`mock_financial_profile_lookup` 在 KB 未命中时已走 Sina live（`data_origin=sina_api`）
- ⑤ 腾讯 PE/PB：`valuation_profile_lookup` 已在综合基本面默认编排
- ④ 巨潮公告：`stock_evidence_api_lookup` 已在 `evidence_gaps` 补数路径；**首轮问股不强制默认调用**（符合「与 RAG 互补」）

---

## 3. 技术方案

### 3.1 新建东财研报元数据层（G1）

**拆分** `em_report_consensus_client` 的列表拉取逻辑，避免共识聚合与元数据 Tool 重复维护。

| 文件 | 动作 |
|------|------|
| `integrations/market_data/em_research_report_client.py` | **新建**。`fetch_em_research_reports(stock_code, *, page_size=20, max_pages=2)` → 标准化 `reports[]` |
| `agents/tools/research_report_metadata_lookup.py` | **新建**。Agent Tool 包装，输出契约见 §3.6 |

**单条 report 字段**（对齐 SKILL.md §2.1）：

```json
{
  "title": "…",
  "org_name": "…",
  "publish_date": "2026-05-10",
  "rating": "买入",
  "rating_change": "维持",
  "predict_this_year_eps": 1.23,
  "predict_next_year_eps": 1.45,
  "pdf_url": "…"
}
```

- HTTP 一律经 `eastmoney_client.em_get`（限流 ≥1s）
- 失败返回 `found=false`、`fallback_used=true`、`fallback_reason`，**不抛未捕获异常**

### 3.2 问股动态编排增强（G2）

**文件**：`agents/stock_tool_plan.py`

新增正则与编排规则：

```python
_INSTITUTION_VIEW_RE = re.compile(
    r"机构怎么看|机构观点|一致预期|研报评级|卖方怎么看|分析师怎么看|目标价",
    re.IGNORECASE,
)
```

| 场景 | `resolve_stock_tool_names` 输出（在白名单过滤后） |
|------|--------------------------------------------------|
| 机构观点类（G2） | `mock_financial_profile_lookup` + `consensus_valuation_lookup` + `research_report_metadata_lookup` |
| 综合基本面（现有） | `mock_financial_profile_lookup` + `valuation_profile_lookup`（不变） |
| 纯财报（现有） | 仅 `mock_financial_profile_lookup` |
| 情景回报（现有） | `valuation_profile_lookup` + `consensus_valuation_lookup` |
| 管线/研发（现有） | `[]` |

**白名单扩展**：

```python
STOCK_TOOL_WHITELIST |= {"research_report_metadata_lookup"}
```

`stock_analysis_agent` 在 LLM 返回 `tool_names` 后仍走 `resolve_stock_tool_names` 保底（机构类问题即使用户/LLM 漏选，规则层补齐）。

### 3.3 Prompt 与引用层（G3）

| 文件 | 改动 |
|------|------|
| `integrations/llm/prompts/agents/stock_analysis.py` | §五工具表增加 `consensus_valuation_lookup`、`research_report_metadata_lookup`；§六「机构怎么看」明确须选 consensus + 研报元数据；JSON 契约 `tool_names` 白名单同步 |
| `integrations/llm/prompts/assembly.py` | 增加 `consensus_valuation_lookup`、`research_report_metadata_lookup` 证据使用说明；机构观点须标注「观点非事实」 |
| `services/citation_catalog.py` | 为 consensus / 研报元数据生成 `citation` 条目（`origin=ths_worth_consensus` / `eastmoney_reportapi`） |

### 3.4 Trace 可观测性（G4）

**文件**：`agents/nodes/tool_call.py`

在 `build_parallel_trace_update` 前，为每个 tool 结果生成 `detail_sections`：

```python
{
  "title": "工具归因",
  "items": [
    {"label": tool_name, "value": f"origin={data_origin}; mock={is_mock}; fallback={fallback_used}"},
    {"label": "attribution", "value": "third_party/a-stock-data (Apache-2.0)"},
    {"label": "source", "value": source_url},
  ],
}
```

- 从各 Tool 标准字段读取：`data_origin`、`is_mock`、`fallback_used`、`source`、`attribution`
- `output_data` 增加 `tool_attributions: list[dict]` 供 raw JSON 弹窗
- **财务 Tool**：当 `data_origin=local_profile_cache` 时 Trace 标注 `fallback_used=true`（相对 live API），避免误判 live PASS

**文件**：`integrations/langgraph/status_phases.py`（可选 P2）

- `on_tool_started` 将工具人类可读名写入资料子项（如「新浪财经财报」「同花顺一致预期」）

### 3.5 数据源状态 API（G5）

**文件**：`services/config_status_service.py`

在 `mock_data` 列表中**追加** live 条目（不删除 KB 条目）：

| type | name | path | status |
|------|------|------|--------|
| `financial_live` | 新浪财经财报 API | `integrations/market_data/sina_finance_client.py` | `ready`（零 key 公开接口） |
| `consensus_live` | 同花顺一致预期 | `integrations/market_data/ths_worth_client.py` | `ready` |
| `report_live` | 东财研报 reportapi | `integrations/market_data/em_research_report_client.py` | `ready` |
| `announcement_live` | 巨潮公告 + 东财快讯 | 已有 `announcement` 行可合并说明 | `ready` |

- **禁止**在 status 响应中写入 Key
- 可选：启动时做一次轻量 probe（如 `paper_code_for('600519')` 列表请求），失败标 `degraded` 而非 `ready`

### 3.6 Tool 输出契约（统一字段）

所有 live Tool 返回须包含：

```python
{
  "tool": "<tool_name>",
  "found": bool,
  "is_mock": False,           # demo 工具才 True
  "data_origin": str,         # sina_api | ths_worth_consensus | eastmoney_reportapi | cninfo_api | local_kb_file | ...
  "fallback_used": bool,
  "fallback_reason": str,     # 可选
  "source": str,              # URL 或 KB 路径
  "attribution": "third_party/a-stock-data (Apache-2.0)",
  "notes": str,
}
```

**`research_report_metadata_lookup` 专有**：

```python
{
  "reports": [...],           # ≤20 条，按 publish_date 降序
  "report_count": int,
  "rating_summary": {"买入": 3, "增持": 2, ...},  # 可选聚合
}
```

### 3.7 HTTP 客户端规范（G6）

| 客户端 | 动作 |
|--------|------|
| `eastmoney_client.py` | `_EM_SESSION.trust_env = False` |
| `ths_client.py` | 评估改 `requests.get(..., trust_env=False)` 或保持 urllib（无代理继承） |
| 新增代码 | 优先 `httpx.AsyncClient(trust_env=False)` 或 `requests` + `trust_env=False` |

### 3.8 注册与编排接线

| 文件 | 动作 |
|------|------|
| `agents/tools/__init__.py` | 注册 `research_report_metadata_lookup` |
| `agents/stock_tool_plan.py` | 白名单 + 机构类规则（§3.2） |
| `services/evidence_gaps.py` | 机构观点缺口 `institution_view_thin` 时可追加 `research_report_metadata_lookup`（与首轮编排互补，非替代） |

---

## 4. 分步实现（建议 Developer 顺序）

| 步骤 | 内容 | 依赖 |
|------|------|------|
| **S1** | `em_research_report_client.py` + 单测（HTTP mock） | 无 |
| **S2** | `research_report_metadata_lookup.py` + 注册 `TOOL_REGISTRY` | S1 |
| **S3** | `stock_tool_plan` 机构类编排 + 白名单 + 单测 | S2 |
| **S4** | `stock_analysis` / `assembly` Prompt + `citation_catalog` | S3 |
| **S5** | `tool_call` Trace `detail_sections` + `tool_attributions` | S2–S4 |
| **S6** | `config_status_service` live 数据源条目 | S1 |
| **S7** | `eastmoney_client.trust_env=False` + 相关客户端审计 | 任意 |
| **S8** | 集成测试 + `REAL_API_TEST=1` 冒烟（见 §5） | S1–S7 |
| **S9** | **前端真实联调** `VITE_USE_MOCK=false`：问股 + 管理端 Trace 验收 | S8 |

---

## 5. 验收映射

### 5.1 用户可见验收（`acceptanceCriteria`）

| AC | 验证方式 | 通过条件 |
|----|----------|----------|
| 未收录创业板基本面 | 客户端问「300xxx 某某公司基本面」（选 T-019 batch 外或 mock 未缓存代码） | 回答含营收/净利/毛利率等 + **报告期**；来源注明新浪或本地 KB，非空编 |
| 机构怎么看 | 问「机构怎么看宁德时代」 | 回答含一致预期情景 **或** 研报列表（评级/EPS）；非「本地证据不足」空答 |
| Trace 归因 | 管理端 Trace → `tool_call` | 见各 Tool 名称、`data_origin`、fallback 边界、Apache-2.0 归因 |
| 失败降级 | 断网或 mock HTTP 5xx（单测） | 不 500；正文说明缺失；测试报告标 fallback，**不得标 live PASS** |
| 边界 | 问「今日盘口/资金流」 | 不走 live 基本面 Tool 主路径（维持 PRD 边界） |

### 5.2 技术验收（`technicalChecks`）

```text
$PY -m ruff check backend/src backend/tests 通过
$PY -m mypy backend/src backend/tests 通过
$PY -m pytest backend/tests/test_financial_profile_lookup.py \
  backend/tests/test_consensus_valuation.py \
  backend/tests/test_research_report_metadata_lookup.py \
  backend/tests/test_stock_tool_plan.py \
  backend/tests/test_tool_call_stock_plan.py \
  backend/tests/test_stock_evidence_api_lookup.py -q 通过
REAL_API_TEST=1 至少 3 条：① Sina 未收录代码 ② THS/东财 consensus ③ 东财研报列表
VITE_USE_MOCK=false：POST /api/chat/query 问股命中 8099；Trace tool_call 含 live attribution
GET /api/data-sources/status 可见 financial_live / consensus_live / report_live
eastmoney_client / sina 客户端 trust_env=False（或等效无代理继承）
```

### 5.3 推荐 REAL_API_TEST 用例

| ID | 输入 | 断言 |
|----|------|------|
| RT-018-01 | `lookup_financial_profile(stock_code=未入库创业板)` | `data_origin=sina_api`，`periods` 非空 |
| RT-018-02 | `lookup_consensus_valuation(stock_code=600519)` | `found=true`，`data_origin` 含 `ths` 或 `eastmoney` |
| RT-018-03 | `research_report_metadata_lookup(stock_code=600519)` | `reports` ≥3，含 `title`+`rating` |
| RT-018-04 | LangGraph 集成「机构怎么看贵州茅台」 | `tool_call` 含 consensus + report_metadata |

---

## 6. 风险与降级策略

| 风险 | 降级 | Trace / 报告要求 |
|------|------|------------------|
| 新浪限流/结构变更 | 回退 KB → 内置样本 → `found=false` | `data_origin` 记录尝试链；`fallback_used=true` |
| 同花顺 HTML 改版 | 东财 `em_report_consensus` → KB 研报摘录 | 标注 `ths_worth_consensus` 失败原因 |
| 东财 reportapi 空列表 | 仅展示 THS 一致预期 + RAG 机构观点 | 不得编造评级 |
| 代码解析失败 | 澄清 `stock_name`；跳过 live Tool | `tool_status=skipped` |
| 网络/代理 | `trust_env=False`；捕获异常 | Tester 报告 **Mock/fallback 验收**，禁止 live PASS |

---

## 7. 文件清单

### 新建

- `backend/src/integrations/market_data/em_research_report_client.py`
- `backend/src/agents/tools/research_report_metadata_lookup.py`
- `backend/tests/test_research_report_metadata_lookup.py`
- `backend/tests/test_stock_live_integration.py`（LangGraph + tool_call 归因，可选合并现有文件）

### 修改

- `backend/src/agents/stock_tool_plan.py`
- `backend/src/agents/tools/__init__.py`
- `backend/src/agents/nodes/tool_call.py`
- `backend/src/integrations/market_data/eastmoney_client.py`
- `backend/src/integrations/market_data/em_report_consensus_client.py`（复用列表 fetch，去重）
- `backend/src/services/config_status_service.py`
- `backend/src/services/citation_catalog.py`
- `backend/src/integrations/llm/prompts/agents/stock_analysis.py`
- `backend/src/integrations/llm/prompts/assembly.py`
- `backend/src/services/evidence_gaps.py`（可选 institution 缺口）
- `backend/tests/test_stock_tool_plan.py`（机构类编排）
- `backend/tests/test_tool_call_stock_plan.py`（Trace detail_sections）

### 不改

- T-019 ingest 脚本与 KB 文件
- 前端页面结构（Trace 通用渲染已支持 `detail_sections`；仅验证联调）
- registry 键 `mock_financial_profile_lookup`（避免破坏现有图与测试）

---

## 8. 系统级经验约束（已写入方案）

1. **任务内前端真实联调**：S9 必须 `VITE_USE_MOCK=false` 浏览器验收 Trace。
2. **httpx / requests `trust_env=False`**：§3.7。
3. **零 key 公开 API**：真实 Key 不进 `docs/**`、`.sdd/**`；东财走 `em_get` 限流。
4. **Tester 不得仅 curl PASS**：须 Trace + 页面 + `REAL_API_TEST`。
5. **fallback 不伪装 live PASS**：`data_origin` + `fallback_used` 双字段 + 测试报告口径。

---

## 9. 是否可立即进入开发

**是。** 基础设施约 70% 已落地；剩余为 **东财研报元数据 Tool（G1）**、**问股编排/Prompt/Trace/状态可观测（G2–G5）** 与 **端到端验收（G7）**。无阻塞依赖；与 T-019（KB 扩容）并行不冲突。

**建议 Developer 从 S1→S3 开始**，完成编排与单测后再做 Trace/状态与前端联调。
