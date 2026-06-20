# T-025 回答组装性能优化（Phase 0～2）— 技术方案

> **任务 ID**：T-025  
> **source_feature**：F01 对话 / F02 Trace / 性能  
> **前置**：T-012 ✅ LangGraph、T-017 ✅ 多轮、T-018 ✅ live Tool  
> **产出日期**：2026-06-20  
> **状态**：待 Developer 执行

---

## 1. 背景与目标

用户反馈 **回答组装（`response_assembly`）节点耗时过长**。Trace 显示该节点占整条链路 wall-clock 的主要部分。

**根因（Orchestrator 探查结论）**：

1. output LLM 输入重复：`evidence_pack` 全量 JSON + `format_citation_context` 再展开工具/RAG
2. stock system prompt ~10k 字，所有路由共用重量级 prompt
3. citation 校验导致首稿 buffer 不推流 + 可能第二次完整 LLM 生成
4. 无 `assembly_profile` 分级、无模板短路、无独立 assembly 模型配置
5. T-018 后工具/evidence 更大，但未在 citation 区展开 consensus/研报 JSON

**本任务目标**（Phase 0 + Phase 1 + Phase 2 一次交付）：

| Phase | 目标 |
|-------|------|
| **0** | Trace 可观测：assembly 子 span、prompt 体积、citation retry 命中率 |
| **1** | Quick Wins：profile 分级、user prompt 去重、首稿流式 + 程序补 citation |
| **2** | 架构：模板短路、assembly 模型配置、agent_summary 驱动润色、citation 区补 T-018 |

**非目标**：

- 复合路由分段输出（Phase 3，本任务不做）
- intent + slot 合并（前置 LLM 合并，本任务不做）
- 修改 LangGraph 拓扑（不增删节点）
- 前端 UI 改版（Trace 通用渲染已支持 `raw_json` / `detail_sections`）

---

## 2. 架构设计

### 2.1 新增模块

```
backend/src/agents/assembly/
├── __init__.py
├── profile.py          # resolve_assembly_profile(state) -> AssemblyProfile
├── prompt_builder.py   # build_assembly_user_prompt(...) 结构化去重
├── citation_fix.py     # patch_missing_citations(content, catalog) 程序补标
└── template.py         # try_template_assembly(state) -> str | None
```

### 2.2 AssemblyProfile 枚举

| profile | 触发条件 | system prompt | max_tokens |
|---------|----------|---------------|------------|
| `template_skip` | `try_template_assembly` 命中 | 无 LLM | 0 |
| `heatmap_primary` | `wants_sector_heatmap` + tiles | `ASSEMBLY_HEATMAP_LITE`（新建，~400 字） | 512 |
| `data_ranking_only` | 仅 `market_ranking_lookup` 有 rows，无 RAG | data lite | 768 |
| `data_calculator` | 仅 calculator/scenario，无排行/RAG | data lite + 测算引导 | 1024 |
| `hotspot_api_primary` | `hotspot_evidence_mode=api_primary` | hotspot + addendum | 1536 |
| `stock_narrative` | `stock_narrative_mode` 且无财务 tool usable | `ASSEMBLY_STOCK_NARRATIVE_LITE`（新建） | 1536 |
| `compound` | `response_kind=compound_stock_data` | 已有短 prompt | 2048 |
| `stock_full` | 默认问股综合 | 现有 `ASSEMBLY_STOCK_PROMPT_BASE` | 2048 |
| `data_default` | 其他问数 | `ASSEMBLY_DATA_PROMPT_BASE` | 1536 |
| `hotspot_default` | 其他热点 | `ASSEMBLY_HOTSPOT_PROMPT_BASE` | 1536 |

`assembly_system_prompt(ctx, response_kind, profile=...)` 扩展签名；lite prompt 放 `prompts/assembly.py`。

### 2.3 User Prompt 去重结构

**禁止**再塞全量 `evidence_pack` JSON。改为：

```text
用户问题：{normalized_query}

【分析骨架】
{agent_summary}

【分析维度】（若有）
{analysis_dimensions 精简 JSON}

【结构化引用与证据】（唯一数据源）
{format_citation_context(...)}

【元信息 flags】（单行 JSON，仅 boolean/enum）
{stock_narrative_evidence_missing, scenario_return_mode, hotspot_evidence_mode, ...}

【多轮对话上下文】（T-017，has_context 时）
...

质检修订建议 / 条件约束块 / heatmap 短答指令（保持现有逻辑）
请直接输出 Markdown 正文。
```

`evidence_pack.tool_result` / `rag_hits` 原文**只**出现在 `format_citation_context`（经 citation 区展开），不再 duplicate。

### 2.4 Citation 策略变更

| 旧行为 | 新行为 |
|--------|--------|
| `buffer_first_draft=True` 当需 citation | **始终**首稿 `stream_to_client=True` |
| 段末缺 citation → 整篇 retry LLM | `patch_missing_citations()` 程序补 `[citation:N]` |
| 零 citation 或缺 `### 参考来源` → full retry | 仍走 **patch retry**：仅追加缺失段落/参考来源节，prompt ≤500 字增量 |
| retry 用完整 user_prompt | retry 用 `build_citation_patch_prompt(missing_sections_only)` |

`citation_fix.py` 复用 `citation_rules.paragraphs_missing_trailing_citations`；对 factual 段落段末补最相关 citation index（规则：财务段→1，估值→valuation index，RAG 关键词匹配 hit index）。

### 2.5 模板短路（Phase 2）

`try_template_assembly(state) -> str | None`：

| 条件 | 模板输出 |
|------|----------|
| 纯热力图（`heatmap_primary`） | 3～6 行口径 + 板块亮点 + 风险提示 |
| 纯排行（仅有 ranking rows，无 RAG，非 board_stocks 复杂解读） | 2～4 行 + 「详见下方排行表」 |
| 纯 local_return_calculator（非 scenario） | 测算假设说明 + 引导交互组件 |

模板正文经 `ensure_public_risk_notice` + `normalize_assembly_citations`；rich blocks 仍由现有 builder 构造；Trace 标记 `assembly_mode=template`。

### 2.6 Settings：assembly 模型（Phase 2）

`backend/src/settings.py` + `config/app.toml` + `_ENV_FIELD_MAP`：

```python
llm_assembly_model: str = ""       # 空则 fallback llm_model
llm_assembly_timeout: str = ""     # 空则 fallback llm_timeout
```

`LLMService._assembly_client()`：优先 assembly 字段，否则 `_output_client()`。

### 2.7 agent_summary 驱动润色（Phase 2）

stock_full / stock_narrative profile 的 system prompt 追加约束块（≤300 字）：

> 你必须在【分析骨架】基础上扩写，不得重新规划分析维度；不得新增 agent_summary 未列出的章节主题；表格数字仅来自【结构化引用与证据】。

### 2.8 format_citation_context 补 T-018

在 valuation 块之后、stock_api 之前插入：

- `consensus_valuation_lookup`：`scenarios` 摘要 JSON（截断）
- `research_report_metadata_lookup`：`reports[:5]` 摘要 JSON

与 `build_citation_catalog` 编号对齐。

### 2.9 Trace 可观测（Phase 0）

`response_assembly` step 的 `raw_json` 增加：

```json
{
  "assembly_profile": "stock_full",
  "assembly_mode": "llm | template",
  "prompt_stats": {
    "system_chars": 9800,
    "user_chars": 6200,
    "citation_context_chars": 4100
  },
  "llm_passes": [
    {
      "pass": "first",
      "latency_ms": 8400,
      "completion_tokens": 1200,
      "streamed": true,
      "model": "..."
    }
  ],
  "citation_retry_triggered": false,
  "citation_patch_applied": true,
  "citation_patch_paragraphs": 2
}
```

`detail_sections` 增加「组装性能」：profile、pass 数、prompt 字符、是否模板。

---

## 3. 实施步骤（Developer 按序）

| 步骤 | 内容 | 关键文件 |
|------|------|----------|
| **S1** | 新建 `assembly/profile.py` + 单测 | `backend/tests/test_assembly_profile.py` |
| **S2** | `prompt_builder.py` 去重 user prompt | 替换 `response_assembly.py` 内联组装 |
| **S3** | `citation_fix.py` + 调整 retry 策略；取消 buffer_first_draft | `citation_rules.py` 可复用 |
| **S4** | `format_citation_context` 补 consensus/研报 | `citation_catalog.py` |
| **S5** | lite system prompts + `assembly_system_prompt(profile=)` | `prompts/assembly.py` |
| **S6** | `template.py` 模板短路 + profile=`template_skip` | `response_assembly.py` |
| **S7** | `llm_assembly_model` settings + `_assembly_client()` | `settings.py`, `service.py` |
| **S8** | Trace raw_json / detail_sections | `response_assembly.py`, `_helpers` 可选 |
| **S9** | 回归单测：streaming / multturn / citation / langgraph execution | 见 §5 |
| **S10** | 更新 `.sdd/experience.md` | 经验沉淀 |

---

## 4. 用户可见验收（acceptanceCriteria）

| AC | 验证方式 | 通过条件 |
|----|----------|----------|
| 问数提速 | 客户端问「今天涨幅前 10 的行业板块」 | 首包 content_delta **明显早于**改前（或 Trace assembly latency 下降）；正文仍含排行解读 + ranking_table 组件 |
| 热力图提速 | 问「行业板块热力图」 | 正文 3～6 行；热力图组件正常；可选 Trace 显示 `assembly_mode=template` |
| 问股质量不退化 | 问「宁德时代 2026 一季报怎么样」 | 仍含多期财务表/解读 + 段末 citation + `### 参考来源`；不出现 BC-006 类幻觉 |
| 机构类 | 问「机构怎么看宁德时代」 | 仍含一致预期或研报列表；citation 区可见 consensus/研报来源 |
| 多轮续问 | 上轮问股后轮问「一季报呢」 | 延续标的口径；user prompt 仍含多轮块 |
| Trace 可观测 | 管理端 Trace → response_assembly | `raw_json` 含 `assembly_profile`、`prompt_stats`、`llm_passes` |
| 流式体验 | 流式对话 | 问股/热点首稿 **边生成边出字**（非长时间空白后 typewriter 一次性吐出） |

---

## 5. 技术验收（technicalChecks）

```text
$PY -m ruff check backend/src/agents/assembly backend/src/agents/nodes/response_assembly.py \
  backend/src/services/citation_catalog.py backend/src/integrations/llm/service.py backend/tests/test_assembly_*.py \
  backend/tests/test_response_assembly_*.py -q 通过

$PY -m pytest backend/tests/test_assembly_profile.py \
  backend/tests/test_assembly_prompt_builder.py \
  backend/tests/test_assembly_citation_fix.py \
  backend/tests/test_assembly_template.py \
  backend/tests/test_response_assembly_streaming.py \
  backend/tests/test_response_assembly_multiturn.py \
  backend/tests/test_langgraph_execution.py -q 通过

新增单测须覆盖：
- resolve_assembly_profile 各 profile 触发
- user prompt 不含全量 evidence_pack.tool_result 重复（assert 字符上限或 mock 计数）
- patch_missing_citations 补段末 citation 后 content_needs_citation_retry=false
- template 短路返回非空且含风险提示
- Trace raw_json 含 assembly_profile

既有 E402（response_assembly import 顺序）可顺带整理；非 blocker。

mypy：本任务新增/核心改动文件通过（全量 mypy 既有债务不阻塞）

VITE_USE_MOCK=false：POST /api/chat/query/stream 问数 + 问股各 1 条；Trace response_assembly 含 prompt_stats
```

---

## 6. 风险与回归要点

| 风险 | 缓解 |
|------|------|
| 去重 prompt 后 LLM 缺字段 | citation 区补 T-018；flags 保留 narrative/scenario 约束 |
| 程序补 citation 标错源 | 仅补「有数字无 citation」段落；标最小相关 index；full retry 作最后兜底 |
| 模板短路内容过薄 | 仅 `template_skip` profile；复杂 query 仍走 LLM |
| bad case BC-006/007 回归 | 单测 + 问股验收用例；`stock_narrative_evidence_missing` 约束块保留 |

参考：`docs/agent/response-bad-case.md` BC-006、BC-007。

---

## 7. 文件清单

### 新建

- `backend/src/agents/assembly/__init__.py`
- `backend/src/agents/assembly/profile.py`
- `backend/src/agents/assembly/prompt_builder.py`
- `backend/src/agents/assembly/citation_fix.py`
- `backend/src/agents/assembly/template.py`
- `backend/tests/test_assembly_profile.py`
- `backend/tests/test_assembly_prompt_builder.py`
- `backend/tests/test_assembly_citation_fix.py`
- `backend/tests/test_assembly_template.py`

### 修改

- `backend/src/agents/nodes/response_assembly.py` — 主重构入口
- `backend/src/services/citation_catalog.py` — consensus/研报 citation 区
- `backend/src/integrations/llm/prompts/assembly.py` — lite prompts + profile 路由
- `backend/src/integrations/llm/service.py` — `_assembly_client()`
- `backend/src/settings.py` — assembly 模型字段
- `backend/config/app.toml` — 默认空 assembly 模型
- `backend/tests/test_response_assembly_streaming.py` — 更新 buffer 行为断言
- `docs/agent/langgraph-flow.md` — §response_assembly 性能字段（可选简短）

### 不改

- LangGraph 节点 ID / 边
- 前端组件（除非 Trace 类型需扩展，通常不需要）
- quality_check 节点逻辑
- fallback_response 路径

---

## 8. 系统级经验约束

1. **数字来自 tool_result**：模板/rich block 不得 LLM 编造排行/财务数字（`.sdd/experience.md` T-012 P3）。
2. **ensure_public_risk_notice 在 content_delta 前**（T-012 assembly 超时经验）。
3. **httpx trust_env=False** 本任务不涉及新 HTTP 客户端。
4. **Tester 不得仅 curl PASS**：须 pytest + Trace raw_json 字段断言。

---

## 9. Developer 完成报告

完成后写入 `.sdd/developer-reports/T-025-completion.md`，含：变更摘要、pytest/ruff 输出、profile 覆盖表、已知限制。

---

## 10. 是否可立即开发

**是。** 无阻塞依赖；与 T-019（KB 扩容）并行不冲突。建议 S1→S5→S2→S3→S4→S6→S7→S8→S9。
