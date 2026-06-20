# T-025 完成报告：回答组装性能优化（Phase 0～2）

> **任务 ID**：T-025  
> **完成日期**：2026-06-20  
> **Developer**：cursor-developer

---

## 变更摘要

### 新增模块 `backend/src/agents/assembly/`

| 文件 | 职责 |
|------|------|
| `profile.py` | `AssemblyProfile` 枚举 + `resolve_assembly_profile()` |
| `prompt_builder.py` | 去重 user prompt（citation 区为唯一数据源） |
| `citation_fix.py` | `patch_missing_citations` / `build_citation_patch_prompt` |
| `template.py` | 热力图/排行/测算模板短路 |

### 核心改动

- **`response_assembly.py`**：接入 profile 分级、模板短路、`_assembly_client()`、首稿始终流式、程序 citation patch + 增量 LLM retry；Trace `raw_json` 与「组装性能」`detail_sections`
- **`citation_catalog.py`**：`format_citation_context` 补 consensus/研报 JSON 块（T-018）
- **`prompts/assembly.py`**：lite system prompts + `assembly_system_prompt(profile=...)`
- **`settings.py` / `config/app.toml`**：`llm_assembly_model` / `llm_assembly_timeout`
- **`service.py`**：`_assembly_client()`（空则 fallback `_output_client` 同配置）
- **`nodes/_helpers.py`**：`raw_json_extra` / `detail_sections` 扩展 trace

---

## Profile 覆盖表

| profile | 触发条件 | system prompt | max_tokens |
|---------|----------|---------------|------------|
| `template_skip` | `try_template_assembly` 命中 | 无 LLM | 0 |
| `heatmap_primary` | 热力图 query + tiles（含其他工具时） | `ASSEMBLY_HEATMAP_LITE` | 512 |
| `data_ranking_only` | 仅排行 rows、无 RAG、非 board_stocks 模板 | `ASSEMBLY_DATA_LITE` | 768 |
| `data_calculator` | 仅非 scenario 测算 | `ASSEMBLY_DATA_CALCULATOR_LITE` | 1024 |
| `hotspot_api_primary` | `hotspot_evidence_mode=api_primary` | hotspot + addendum | 1536 |
| `stock_narrative` | narrative 且无财务 tool | `ASSEMBLY_STOCK_NARRATIVE_LITE` | 1536 |
| `compound` | `compound_stock_data` | 已有短 prompt | 2048 |
| `stock_full` | 默认问股 | `ASSEMBLY_STOCK_PROMPT_BASE` + 润色约束 | 2048 |
| `data_default` | 其他问数 | `ASSEMBLY_DATA_PROMPT_BASE` | 1536 |
| `hotspot_default` | 其他热点 | `ASSEMBLY_HOTSPOT_PROMPT_BASE` | 1536 |

---

## 质量门禁

```text
$PY -m ruff check backend/src/agents/assembly backend/src/agents/nodes/response_assembly.py \
  backend/src/services/citation_catalog.py backend/src/integrations/llm/service.py \
  backend/tests/test_assembly_*.py backend/tests/test_response_assembly_*.py -q
→ 通过

$PY -m pytest backend/tests/test_assembly_profile.py \
  backend/tests/test_assembly_prompt_builder.py \
  backend/tests/test_assembly_citation_fix.py \
  backend/tests/test_assembly_template.py \
  backend/tests/test_response_assembly_streaming.py \
  backend/tests/test_response_assembly_multiturn.py \
  backend/tests/test_langgraph_execution.py -q
→ 37 passed, 6 warnings in ~26s
```

---

## 已知限制

- 程序 citation patch 按关键词启发式选 index，极端段落可能仍需 LLM patch retry
- `template_skip` 与 `heatmap_primary` 在纯热力图 query 时优先模板；多工具并存时走 LLM lite prompt
- 全量 `mypy backend/src` 既有债务未在本任务清零；新增 assembly 模块与 `response_assembly` 重构已 ruff/pytest 验证

---

## 修改/新增文件清单

**新建**

- `backend/src/agents/assembly/__init__.py`
- `backend/src/agents/assembly/profile.py`
- `backend/src/agents/assembly/prompt_builder.py`
- `backend/src/agents/assembly/citation_fix.py`
- `backend/src/agents/assembly/template.py`
- `backend/tests/test_assembly_profile.py`
- `backend/tests/test_assembly_prompt_builder.py`
- `backend/tests/test_assembly_citation_fix.py`
- `backend/tests/test_assembly_template.py`

**修改**

- `backend/src/agents/nodes/response_assembly.py`
- `backend/src/agents/nodes/_helpers.py`
- `backend/src/services/citation_catalog.py`
- `backend/src/integrations/llm/prompts/assembly.py`
- `backend/src/integrations/llm/service.py`
- `backend/src/settings.py`
- `backend/config/app.toml`
- `backend/tests/test_response_assembly_streaming.py`
- `backend/tests/test_response_assembly_multiturn.py`
- `backend/tests/test_langgraph_execution.py`
- `.sdd/experience.md`

经验已追加到 `.sdd/experience.md`

**本功能已完成，等待 Orchestrator 调度 Tester 验证。**
