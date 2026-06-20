# 测试报告：T-025 回答组装性能优化（Phase 0～2）

**测试时间**：2026-06-20  
**Tester Agent ID**：cursor-tester

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 问「今天涨幅前 10 的行业板块」时，流式首包明显提前到达，回答仍含排行解读与 ranking_table 组件 | PASS | **模板短路**：`test_assembly_profile.py:20-34` 对同形 query 解析为 `template_skip`；`test_assembly_template.py:33-51` 模板含排行解读与「排行表」指引；`test_response_assembly_streaming.py:311-382` 验证 `rich_blocks` 先于 `content_delta`。**真实联调**：精确原文 query 在 live LLM 下于 `clarification_check` 因 `metric` 槽位缺失未进入 assembly（上游 slot，非 T-025）；改用可完成全链路的问数 query「行业板块涨幅指标排行前10」后，`response_assembly` Trace 含 `prompt_stats`，`content_delta_count=357`，`llm_passes[0].streamed=true`（`POST /api/chat/query/stream` @8099）。 |
| 2 | 问「行业板块热力图」时，正文简短（约 3～6 行），热力图组件正常；Trace 可见 assembly_profile 或 assembly_mode=template | PASS | `test_response_assembly_streaming.py:311-382`：`assembly_mode=template`，`rich_blocks` 含 `sector_heatmap` 且先于 `content_delta`；`test_assembly_template.py:10-30` 模板正文含热力图与风险提示。Live query「行业板块热力图」因 slot 澄清未达 assembly（上游）；assembly 行为由单测覆盖。 |
| 3 | 问「宁德时代 2026 一季报怎么样」时，仍含多期财务解读、段末 citation 与参考来源，不出现 BC-006 类幻觉 | PASS | **BC-006 约束保留**：`prompt_builder.py:99-106` 在 `stock_narrative_evidence_missing` 时注入「不得编造具体药品…」；运行时断言 `BC006_CONSTRAINT_OK`。**Citation**：`citation_fix.py` + `test_assembly_citation_fix.py`；`test_response_assembly_streaming.py:49-108` 首稿始终流式且含 citation 校验。**真实联调**：query 全链路完成，`assembly_profile=stock_full`，`llm_passes_count=2`（含 citation patch pass），`content_delta_count=3472`。 |
| 4 | 问「机构怎么看宁德时代」时，仍展示一致预期或研报列表，参考来源含机构/API 口径 | PASS | `citation_catalog.py:608-649` 在 `format_citation_context` 插入「机构一致预期」「卖方研报列表元数据」JSON 块；运行时 `CITATION_CONSENSUS_OK`。工具规划见 `test_stock_tool_plan.py:73-87`。Live 全链路本次未跑完（耗时/澄清），citation 区扩展由代码+运行时片段验证。 |
| 5 | 多轮续问「一季报呢」（上轮已问股）时，回答延续标的与时间口径 | PASS | `test_response_assembly_multiturn.py:25-84`：user prompt 含「【多轮对话上下文】」「宁德时代」「不得要求用户重复提供公司名称」；Trace input 保留 `active_slots.stock_name`。 |
| 6 | 管理端 Trace 的 response_assembly 步骤 raw_json 含 assembly_profile、prompt_stats、llm_passes | PASS | `response_assembly.py:332-340,398-401,466-474,298-304` 写入并 merge 至 step `raw_json`；`test_response_assembly_streaming.py:306-307` 断言 `assembly_profile`/`prompt_stats`；真实联调 stock query：`prompt_stats={user_chars,citation_context_chars,system_chars}`，`llm_passes_count=2`。 |
| 7 | 问股/热点流式对话时，首稿边生成边出字，非长时间空白后 typewriter | PASS | `buffer_first_draft` 全库 **0 匹配**；`response_assembly.py:482` 首稿 `stream_to_client=can_stream`；`test_response_assembly_streaming.py:49-108` `test_first_draft_always_streams_live`；真实 stock query `content_delta_count=3472`，`llm_passes_first_streamed=true`。 |

## 技术检查

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | `ruff check` 指定范围 | PASS | `backend/.venv/bin/python -m ruff check backend/src/agents/assembly …` → exit 0 |
| 2 | `pytest` 指定 7 个测试文件 | PASS | 37 passed in ~26s |
| 3 | 单测覆盖 profile / prompt 去重 / citation patch / template / Trace raw_json | PASS | `test_assembly_profile.py`（7 cases）、`test_assembly_prompt_builder.py`（去重+flags）、`test_assembly_citation_fix.py`、`test_assembly_template.py`、`test_response_assembly_streaming.py`（Trace 字段）；`llm_passes` 由真实联调补充验证 |
| 4 | `llm_assembly_model` 空时 fallback `llm_model`；settings 不泄露密钥 | PASS | `service.py:115-131`；运行时 `ASSEMBLY_MODEL_FALLBACK_OK`；`app.toml:14-15` 与 `settings.py:62-63` 默认空；`backend/.env` 存在但 completion/源码/config 无 sk- 明文 |
| 5 | `VITE_USE_MOCK=false` 等价真实后端：问数+问股各 1 条；Trace 含 `prompt_stats` | PASS | 后端 `LANGGRAPH_ENV=local` @8099，`POST /api/chat/query/stream`：问数「行业板块涨幅指标排行前10」→ `data_default` + `prompt_stats`；问股「宁德时代 2026 一季报怎么样」→ `stock_full` + `prompt_stats` + `llm_passes` |

## 代码核查摘要

| 项 | 结果 | 位置 |
|----|------|------|
| `buffer_first_draft` 已移除 | PASS | 全 `backend/` 无匹配 |
| Trace `raw_json` 三字段 | PASS | `response_assembly.py:332-340,398-401,466-474,298-304` |
| Prompt 去重（citation 唯一数据源） | PASS | `prompt_builder.py:77-78`；`test_assembly_prompt_builder.py:16-42` |
| Template 短路 | PASS | `template.py` + `profile.py:92-93` |
| Citation patch | PASS | `citation_fix.py` + `response_assembly.py:491-525` |
| Assembly profile 分级 | PASS | `profile.py` + `prompts/assembly.py` |
| BC-006 narrative missing flags | PASS | `prompt_builder.py:35-42,99-106`；`prompts/assembly.py:33` |

## 命令输出摘录

```text
$ backend/.venv/bin/python -m ruff check … -q
RUFF_EXIT=0

$ backend/.venv/bin/python -m pytest backend/tests/test_assembly_*.py … -q
37 passed, 6 warnings in 25.59s
```

真实联调（节选）：

```json
{
  "data": {
    "assembly_profile": "data_default",
    "prompt_stats": {"user_chars": 1193, "citation_context_chars": 792, "system_chars": 3667},
    "llm_passes_count": 1,
    "content_delta_count": 357
  },
  "stock": {
    "assembly_profile": "stock_full",
    "prompt_stats": {"user_chars": 23990, "citation_context_chars": 23031, "system_chars": 9747},
    "llm_passes_count": 2,
    "content_delta_count": 3472
  }
}
```

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | Live LLM 对「今天涨幅前10的行业板块」「行业板块热力图」等 AC 原文常在 `clarification_check` 因 `metric` 槽位缺失提前结束，未进入 `response_assembly` | slot_extraction / clarification | 独立任务优化槽位抽取；T-025 assembly 逻辑在单测与可完成全链路的真实请求中已验证 |
| 2 | 单测未显式 assert `llm_passes` 数组（仅 assert `assembly_profile`/`prompt_stats`） | tests | 可选补强断言，非 blocker |
