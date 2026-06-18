# T-012 修复轮次 — Developer Report

> **任务**：LangGraph 真实编排（第 1 次 FAIL 修复）  
> **完成日期**：2026-06-15  
> **状态**：待 Tester 第 2 轮验收

---

## 修复摘要

针对 `.sdd/test-reports/test-T-012.md` 中 P0/P1 问题完成修复，本地质量门禁已全部通过。

| 问题 | 修复措施 |
|------|----------|
| 热点 `response_assembly` LLM 超时 → 空答 | `_compact_evidence_for_prompt()` 压缩 evidence；`LLMClientError` 时 `_fallback_assembly_content()` 降级；`runner` 空 `final_response` 兜底 |
| 问股缺「不构成投资建议」 | 新增 `ensure_public_risk_notice()`；`response_assembly` / `runner` 统一追加；流式路径在 emit 前补全风险提示后缀 |
| pytest 3 项失败 | intent prompt 文案、KB 文件计数动态对齐、`conftest` 补 hotspot RAG mock |
| ruff 36 errors | 全量修复 import/格式与局部 lint |
| mypy 44 errors | 类型收窄、`cast`、测试注解、`pyproject.toml` tests override |

---

## 关键代码变更

| 文件 | 变更 |
|------|------|
| `backend/src/agents/nodes/response_assembly.py` | evidence 压缩、LLM 降级、风险提示在 buffered/stream 输出前注入 |
| `backend/src/services/message_sanitizer.py` | `ensure_public_risk_notice()` |
| `backend/src/integrations/langgraph/runner.py` | 空响应兜底 + 风险提示 |
| `backend/src/integrations/llm/prompts/intent.py` | 补充「不得由模型自由测算」表述 |
| `backend/tests/conftest.py` | hotspot RAG mock 方法补全 |
| `backend/tests/test_rag_service.py` | KB md 计数与仓库动态对齐 |
| `backend/tests/test_response_assembly_streaming.py` | 断言适配强制风险提示 |
| 多文件 | mypy/ruff 收尾（`citation_rules`、`hotspot_agent`、`tool_call` 等） |

---

## 质量门禁（2026-06-15）

| 检查 | 结果 |
|------|------|
| `ruff check backend/src backend/tests` | **PASS** |
| `mypy backend/src backend/tests` | **PASS**（179 files） |
| `pytest backend/tests` | **255 passed**, 8 skipped |

---

## 待 Tester 复验项

1. **真实联调**（8098，`LANGGRAPH_ENV=local`）：热点「机器人板块政策催化」不再空答；问股「宁德时代基本面」末尾含标准风险提示。
2. **验收标准 1～4** 与 Trace 节点一致性（首轮已通过项应保持）。
3. 前端 `type-check` / `lint` / `build`（首轮已通过，本轮未改前端逻辑，可抽检）。

---

## 用户操作说明

1. **重启后端**使代码生效。
2. 可选自测：热点 / 问股各提一问，确认正文非空且含「以上内容仅为信息整理，不构成投资建议。」
3. 调度 **Tester** 执行 T-012 第 2 轮验收。

---

**修复轮次已完成，等待 Tester 复验。**
