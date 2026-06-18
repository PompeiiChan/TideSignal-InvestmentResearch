# 测试报告：T-020 回答生成过程状态时间线（展开/折叠）

**测试时间**：2026-06-18 17:28
**Tester Agent ID**：cursor-tester

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 6 步主链路 + 第 3/4 步动态内容 | PASS | `test_status_phases.py::test_main_flow_step_sequence` 通过；`step_start` 含理解/识别/专家/资料/审核/生成 6 步文案 |
| 2 | 流式首包折叠 + 可回看 | PASS | 主链路 SSE：`response_stream_start` 在首个 `content_delta` 之前；`ProgressTimelineView` + `applyResponseStreamStart` 实现折叠与 `toggleMessageProgressTimeline` 回看 |
| 3 | 历史消息独立状态 | PASS | `toggleMessageProgressTimeline` 按 `messageId` 更新；`finalizeStreamedQuery` 保留 `pendingTimeline` 且 `collapsed: true` |
| 4 | 澄清/兜底分支 | PASS | **本轮复验重点**：`runner.py:291-295` 非流式路径先 `on_response_stream_start()` 再 `_drain_stream_queue` 后 `yield content_done`；前端 `content_done` 分支（`useInvestmentStore.ts:340-342`）在 `!timeline.collapsed` 时兜底调用 `applyResponseStreamStart`；`test_clarification_stream_emits_response_stream_start_before_content_done` 与 `test_fallback_stream_emits_response_stream_start_before_content_done` 均断言 `response_stream_start` 在 `content_done` 之前且无 `content_delta` |
| 5 | 不展示未执行步骤、折叠过渡 | PASS | `test_clarification_branch_stops_before_expert_match` / `test_fallback_branch_suffix` 通过；`index.css` 含 `max-height`/`opacity` 过渡 |
| 6 | VITE_USE_MOCK=false 真实 stream 联调 | PASS | `frontend/.env` 为 `VITE_USE_MOCK=false`、`VITE_API_BASE_URL=/api`；`chat.ts` 走真实 `/api/chat/query/stream`；ASGI 集成测试（澄清/兜底/主链路）均通过 |

## technicalChecks

| 检查项 | 结果 | 说明 |
|--------|------|------|
| ruff | PASS | `.venv/bin/python -m ruff check src tests` 全绿 |
| pytest（status_phases / stream） | PASS | `test_status_phases` 4/4；`test_langgraph_chat` 含澄清/兜底 2 例新增；`test_langgraph_runner_stream` 2/2；`test_response_assembly_streaming` 相关用例通过 |
| pytest（全量） | 超出范围 | 265 passed / 1 failed（`test_sessions_layout.py`，与 T-020 无关） |
| frontend type-check / lint | PASS | `npm run type-check`、`npm run lint` 通过 |
| SSE 与需求 §7 对齐 | PASS | 澄清/兜底非流式路径现已下发 `response_stream_start`；`test_non_streaming_path_drains_response_stream_start_before_content_done` 验证 drain 顺序 |
| regenerate 一致性 | PASS | `regenerateMessage` 复用 `runChatStream` 与相同 SSE 处理器 |
| VITE_API_BASE_URL=/api | PASS | `frontend/.env` 已配置 |

## 本轮修复验证（对比第 1 轮 FAIL）

| # | 上轮问题 | 状态 | 证据 |
|---|----------|------|------|
| 1 | 澄清/兜底非流式路径 SSE 缺失 `response_stream_start` | 已修复 | `runner.py` 新增 `_drain_stream_queue` 冲刷；集成测试 2 例 + 单元测试 1 例通过；前端 `content_done` 兜底折叠 |

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | `test_sessions_layout.py` 1 例失败 | sessions/layout | 独立任务修复 |
