# 测试报告：T-011 Rerank 重排

**测试时间**：2026-06-15 14:10 CST  
**Tester Agent ID**：cursor-tester  
**轮次**：第 1 次验收

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 研报/公告类问题，引用顺序体现重排相关性 | **PASS** | 真实联调「宁德时代基本面怎么样」：`rag_retrieval` 重排后 Top1 为 `research_300750_dwzq_sec_000_000`（rerank_score=0.8045），重排前 hybrid Top1 为 `research_300750_dwzq_sec_030_001`（0.65），顺序已变化；摘要与最终命中研报标题一致 |
| 2 | 管理端 Trace RAG 节点可见重排前后/分数 | **PASS** | `step_007` 含 `detail_sections`：「检索状态」「重排前候选」(8 条 hybrid_score)、「重排后结果」(8 条 rerank_score)；`GET …/steps/step_007/raw` → `output.rerank_connected=true`，`rerank_before`/`rerank_after` 各 8 条 |
| 3 | 系统设置页展示 Rerank 字段名与 ready，无真实密钥 | **PASS** | `GET /api/config/status` → `硅基流动 Rerank` status=ready，fields=`RERANK_API_KEY / RERANK_BASE_URL / RERANK_MODEL`；`SettingsPage.tsx` 仅展示 status 与 fields 列表，不渲染 Key 值 |

## 技术检查

| 检查项 | 结果 | 证据 |
|--------|------|------|
| `pytest backend/tests/test_rerank.py` | **PASS** | 4 passed, 1 skipped（`REAL_API_TEST` 冒烟）；含重排前后快照、失败降级 `logger.warning`、Trace 段落断言 |
| `ruff` / `mypy` / 全量 pytest | **PASS**（继承 T-012 门禁） | 2026-06-15 全量 255 passed；本任务抽检 `integrations/rerank/client.py` |
| 前端 type-check / lint / build | **PASS**（继承 T-012 门禁） | 本轮未改前端 Rerank 逻辑 |
| `RERANK_*` 从 `.env` 读取 | **PASS** | `settings.py` + `config_status_service.py`；`docs/**` 无 Key 泄露 |
| httpx `trust_env=False` | **PASS** | `integrations/rerank/client.py:65` |
| `GET /api/config/status` Rerank ready | **PASS** | Key 已配置时 status=ready |
| `GET /api/data-sources/status` | **PASS** | `rerank_provider: siliconflow · Qwen/Qwen3-Reranker-8B` |
| 真实 Rerank 调用（非 mock） | **PASS** | 8099 全链路问股触发真实 Rerank；`rerank_connected=true`，非静态 hybrid 排序 |
| Rerank 失败不静默吞错 | **PASS** | `test_search_chunks_rerank_failure_falls_back_with_warning` 断言 `logger.warning` + `retrieval_mode=hybrid` |
| `frontend/.env` `VITE_API_BASE_URL=/api` | **PASS** | 静态确认 |

## 真实联调摘要（8099，`LANGGRAPH_ENV=local`）

| 用例 | Trace 节点 | Rerank | 重排前 Top1 | 重排后 Top1 |
|------|-----------|--------|-------------|-------------|
| 宁德时代基本面怎么样 | `rag_retrieval` (step_007) | 已启用 | `…sec_030_001` hybrid 0.65 | `…sec_000_000` rerank 0.8045 |

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | LangGraph Trace 步骤顶层 `raw_json` 仅含 input/output 包装，重排明细需展开 `/raw` 或读 `detail_sections` | trace_recorder | 可选增强：扁平化 `rerank_before/after` 到步骤 `raw_json` 顶层 |
| 2 | `test_rerank_service_real_api_smoke` 需 `REAL_API_TEST=1` 才跑 | 测试 | 全链路联调已覆盖真实 Rerank，非阻塞 |
