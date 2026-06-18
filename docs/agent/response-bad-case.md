# Response Bad Case 收集

> 用途：记录线上/验收中发现的 **回答质量 Bad Case**（含 RAG、工具链、组装、引用），便于归因、排期修复与回归验收。  
> 维护原则：每条案例写清 **现象 → 理想态 → 归因 → 修复状态**；修复后更新状态并链到相关 PR/测试。

---

## 案例索引

| ID | 场景 | 类型 | 状态 |
|----|------|------|------|
| BC-001 | 宠物行业误引家纺研报 | RAG + Citation | 已修复 |
| BC-002 | 宠物复合题 THS 全市场误用 | 工具链 | 已修复（Phase A+B） |
| BC-003 | 热点正文有同花顺、参考来源为空 | Citation / 组装 | 已修复 |
| BC-004 | 创新药管线误走财务分析 | 工具编排 | 已修复 |
| BC-005 | 创新药管线补数用巨潮薄公告、缺研报拆解 | RAG + 工具链 | 已修复（系统侧）；待 KB 入库 |
| BC-006 | 恒瑞管线只提 PD-1/L1、无研报引用（幻觉+误检索） | RAG + 组装 | 已修复（系统侧）；待 KB 入库 |
| BC-007 | 海天 2025 年报营收误走澄清（缺 document_id） | 预处理 / 澄清 | 已修复 |

---

## BC-001 宠物行业问答误引「睡眠经济 / 家纺」研报

### 用户问题（示例）

> 宠物行业是否值得看好？逻辑、分类、关注公司、最近市场热度怎么样？

### 现象

- 正文/RAG 与「宠物」弱相关，却引用 **纺织业 / 睡眠经济 / 家纺** 行业研报。
- 参考来源出现与问题无关的长文 citation。

### 理想态

- 本地 KB **无宠物专题**时：明确写「本地未覆盖宠物赛道」，用东财板块热度、行业资讯等 **可核验** 材料；**不得**用低分 RAG 硬贴无关研报。
- 参考来源仅保留正文实际引用的 `[citation:N]`。

### 归因

1. **RAG**：知识库无宠物内容，向量/BM25 低分误命中「睡眠经济」等语义邻近词。
2. **检索策略**：scoped 空结果时曾回退全库 `retrieve()`，放大误命中。
3. **Citation**：`build_citation_catalog` 对全部 RAG hit 编目，`sanitize_reference_section` 修复前未严格对齐正文引用。

### 修复（摘要）

- `HOTSPOT_MIN_SCORE = 0.40`；热点 scoped 空结果不再回退全库。
- `sanitize_reference_section` 只保留正文已出现的 citation 对应来源行。
- 测试：`test_citation_catalog.py`、`test_hotspot_*`

### 回归要点

- 宠物类问题参考来源 **不得** 出现家纺/睡眠经济研报（除非正文明确引用且用户问及相关）。

---

## BC-002 宠物复合题：热度走 THS 全市场、未用板块排行

### 用户问题（示例）

同上（含「最近市场热度」）。

### 现象

- `api_primary` + `hotspot_industry_only` → RAG 0 条。
- 仅 `hotspot_fact_lookup` + `hotspot_signal_lookup`；**未调用** `market_ranking_lookup` / `sector_heatmap_lookup`。
- THS 关键词「宠物行业」未命中仍返回 **全市场强势股**（AI 算力、商业航天等），被写成主题热度。

### 理想态

- 「最近热度」→ **东财板块/概念排行 + 热力**，非 THS 全市场榜。
- THS 未命中 → `topic_matched=false`，禁止用无关 `reason` 标签。
- 复合题拆子任务：逻辑 / 标的 / 盘面热度。

### 归因

1. **工具编排**：热点链路未挂问数类行情工具。
2. **THS 客户端**：关键词未命中时回退全量强势股列表。
3. **Prompt**：未约束 `topic_matched=false` 时的写法。

### 修复（摘要）

- Phase A：`ths_client` 未命中不回退；组装层约束。
- Phase B：`hotspot_tool_plan` + `tool_call` + `response_assembly` 挂 `market_ranking_lookup` 等。
- 测试：`test_hotspot_tool_plan.py`、`test_hotspot_signal_lookup.py`

### 回归要点

- Trace 含 `market_ranking_lookup`；THS `topic_matched=false` 且 `stock_count=0`。

---

## BC-003 热点回答正文提同花顺、参考来源为空

### 现象

- Response 正文描述「同花顺盘面信号 / 东财快讯」等。
- 文末 **`### 参考来源` 整段缺失**。

### 理想态

- API 工具（同花顺、东财快讯、板块排行）应有 **引用编号**，参考来源与正文 citation 一致。

### 归因

1. `build_citation_catalog` **未**为 `hotspot_signal_lookup` / `market_ranking_lookup` 等 API 分配 `[citation:N]`。
2. `sanitize_reference_section`：参考来源行的编号未出现在正文 → 整段删除。

### 修复（摘要）

- API 工具纳入 citation catalog + `format_citation_context`。
- 正文有 citation 但参考来源被清空时 **自动重建** 来源节。
- 测试：`test_citation_catalog.py`（hotspot API tools）

### 回归要点

- `api_primary` 且无 RAG 时，参考来源仍列出同花顺/东财等 API 条目。

---

## BC-004 创新药管线问题误走财务 / 估值工具

### 用户问题（示例）

> 恒瑞医药的创新药管线？

### 现象

- 调用 `mock_financial_profile_lookup`、`valuation_profile_lookup`。
- 回答偏 **营收、利润、PE/PB 多期表**，而非管线梳理。

### 理想态

- **不调用** 结构化财务/估值工具（除非用户同时问业绩、估值）。
- 以 **年报 / 研报** 中「研发、管线、适应症、临床阶段」章节为主，输出管线总览与品种拆解。

### 归因

1. `stock_tool_plan` 默认 `mock_financial_profile_lookup` + 估值。
2. 子 Agent 默认 `analysis_dimensions` 为「基本面、盈利能力、估值水平」。
3. 组装 prompt 优先解读 `tool_result` 财务数字。

### 修复（摘要）

- `is_qualitative_business_query`（管线、在研、创新药等）→ `needs_tool=false`，跳过财务工具。
- `stock_narrative_mode` + 定向 RAG；prompt/组装增加「管线类」约束。
- 测试：`test_stock_tool_plan.py`、`test_evidence_gaps.py`

### 回归要点

- Trace **无** `mock_financial_profile_lookup` / `valuation_profile_lookup`。
- `execution_plan.stock_narrative_mode=true`。

---

## BC-005 创新药管线：补数用巨潮薄公告，缺研报深度拆解

### 用户问题（示例）

> 恒瑞医药的创新药管线？

### 现象

- 不再走财务工具（BC-004 修复后）。
- 本地 KB **无恒瑞** 专属文档时，gap 补数调用 `stock_evidence_api_lookup`（巨潮/东财资讯）。
- 返回多为 **零散临床启动、实验进展类公告**，回答 **单薄**，无法形成管线总览表。

### 理想态

| 优先级 | 证据类型 | 用途 |
|--------|----------|------|
| 1 | **公司研报** `company-reports/` | 管线分阶段拆解、品种逻辑、催化剂 |
| 2 | **行业研报** `industry-reports/` | 赛道格局、对标、政策与支付 |
| 3 | **年报** `financials/` 研发章节 | 官方披露的在研/上市品种列表 |
| 4 | 巨潮/快讯 API | 仅作 **事件补点**，不作主线骨架 |

- 本地无该公司研报时：明确「未收录恒瑞公司研报」，可引用 **医药行业研报** 中创新药/管线通用框架 + 公开口径，**禁止**用几条公告拼凑完整管线表。

### 归因

1. **RAG 策略**：`stock_narrative` 仅 `retrieve_targeted` 泛检索，未 **按路径加权** 优先 `company-reports/`、`industry-reports/`。
2. **Gap 补数**：`company_rag_missing` 触发 `stock_evidence_api_lookup`，公告时效新但 **信息密度低**。
3. **知识库覆盖**：`companies.md` / `financials/` 暂无恒瑞（600276），需运营侧入库；系统侧应先用好已有研报。

### 修复（摘要）

- `retrieve_stock_narrative`：`company-reports/`（45%）+ `industry-reports/`（35%）+ `financials/`（20%）分路径加权。
- 叙事类 gap **禁用** `stock_evidence_api_lookup`，仅二次研报向 RAG。
- Prompt：管线类「研报为主、公告为辅」。
- 运营待办：恒瑞等公司研报/年报入库（见 `knowledge-base-ingestion.md`）。

### 状态

**已修复（系统侧）**；恒瑞等公司无 KB 文档时回答仍受限于库存，需运营入库。

### 回归要点

- Trace 首轮 RAG 命中路径含 `company-reports/` 或 `industry-reports/`（有库存时）。
- 叙事类 gap 补数 **不出现** `stock_evidence_api_lookup`（除非用户明确问「最新公告」）。
- 回答结构含：阶段分布 / 核心品种 / 商业化节奏（有证据时）。

---

## BC-006 恒瑞管线只提 PD-1/PD-L1、无券商研报引用

### 用户问题（示例）

> 恒瑞医药的创新药管线？

### 现象

- 回答 **极其单薄**，只提到 PD-1、PD-L1 等少数靶点。
- **没有**引用任何 `company-reports/` 券商深度研报。
- Trace 中 RAG 可能误命中 **寒武纪等其他公司年报**，或完全无研报路径。

### 理想态

- 有恒瑞公司研报：按研报输出分阶段管线表、核心品种、适应症。
- 无本地研报：声明「未收录公司深度研报」，**不得**无 citation 列举 PD-1 等药品名。

### 归因

1. **KB 无恒瑞**：全库无「恒瑞 / PD-1」文本；无 `600276` 公司研报。
2. **RAG bug**：`filter_hits_by_entity` 无实体匹配时回退高分无关文档（寒武纪年报）。
3. **LLM 幻觉**：证据不足时用常识编造 PD-1/PD-L1。

### 修复（摘要）

- `filter_stock_narrative_hits` + `narrative_strict` 检索。
- `stock_narrative_evidence_missing` 组装约束，禁止无 citation 列药品。
- **待运营**：导入恒瑞 `company-reports/` 深度研报。

### 回归要点

- 未入库：RAG 0 或仅行业创新药研报；正文不编造 PD-1。
- 入库后：命中 `company-reports/*`，参考来源含券商标题。

---

## 附录：Bad Case 记录模板

```markdown
## BC-XXX 标题

### 用户问题（示例）
> …

### 现象
- …

### 理想态
- …

### 归因
1. …

### 修复（摘要）
- …

### 回归要点
- …
```

---

## BC-007 海天味业 2025 年报营收误走澄清追问

### 用户问题（示例）

> 关于海天味业 2025 年年报营收数据的查询  
> 请查询海天味业2025年年度报告中的营业收入数据

### 现象

- 意图识别为 `document_qa`，槽位已抽出 `stock_name` / `time_range` / `metric`，但 `slot_extraction` 仍标记 `missing_slots: ["document_id"]`。
- `clarification_check` 的 `missing_core` 已因 KB 可解析而跳过 `document_id`，但 `non_defaultable_missing` 分支仍因上游 `missing_slots` 触发澄清。
- 用户收到「尚未收录 2025A」「请确认 A 股标的」等 **无需补充** 的追问，而非直接给出营收 **288.73 亿元**。

### 理想态

- 公司名 + 年报/营收类问句且本地 KB 有对应财报 → **直接 RAG 回答**，不要求 `document_id`，不让用户确认标的范围。
- 路由改写为 `stock_analysis_agent` → `rag_retrieval` 命中 `ann_603288_2025`。

### 归因

1. **澄清门控**：`_normalize_slot_lists_for_clarification` 仅处理 `stock_analysis` 可选槽位，未剥离 KB 可解析 `document_qa` 的 `document_id`。
2. **意图与槽位不一致**：`document_qa` + 完整财务槽位应视同问股财报子场景。

### 修复（摘要）

- `clarification_check._normalize_slot_lists_for_clarification`：`document_qa` 且 `is_kb_resolvable_document_query` 时从 `missing_slots` 剔除 `document_id`。
- 测试：`test_langgraph_preprocessing.py`（澄清 + 路由至 `stock_analysis_agent`）。

### 回归要点

- 「请查询海天味业2025年年度报告中的营业收入数据」→ `need_clarification=false`，`route_target=stock_analysis_agent`，正文含营收数值。

---

## 变更日志

| 日期 | 说明 |
|------|------|
| 2026-06-16 | BC-007：海天 2025 年报营收 document_id 误澄清 |
| 2026-06-14 | BC-006：恒瑞管线 PD-1 幻觉 + 寒武纪年报误检索；叙事 RAG 严格过滤 |
