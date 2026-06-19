# 用户验收清单：路线图 T-021-P1 估值工具丰富度

**版本检查点**：开发完成后以 `git rev-parse --short HEAD` 为准  
**验收环境**：`VITE_USE_MOCK=false` · 后端 **8099** · 前端 **5199** · `LANGGRAPH_ENV=local`  
**参考**：`docs/agent/tool-richness-roadmap.md` §三

---

## 0. 验收前准备

| # | 检查项 | 操作 | 通过 □ |
|---|--------|------|--------|
| 0.1 | 后端就绪 | `curl -s http://127.0.0.1:8099/api/health` 返回 `status: ok` | |
| 0.2 | 前端联调 | 浏览器打开 http://127.0.0.1:5199 ，`frontend/.env` 为 `VITE_USE_MOCK=false` | |
| 0.3 | LangGraph | `GET /api/config/status` → `orchestration.status` 为 `ready` | |
| 0.4 | 管理端 Trace | 客户端提问后切到 **管理端**，右侧 **Trace 链路** 可展开 `tool_call` 节点 | |
| 0.5 | 网络 | 本机可访问腾讯 `qt.gtimg.cn` 与东财 `datacenter-web.eastmoney.com` | |

**自动化预检（可选）**：

```bash
cd backend && PYTHONPATH=.. ../.venv/bin/python -m pytest \
  tests/test_em_valuation_history_client.py \
  tests/test_stock_tool_plan.py -q
```

---

## 1. 估值问题：当前 + 历史分位

**提问（建议新建会话）**：

> 长春高新估值贵不贵？

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 1.1 | 意图路由 | Trace：`intent_id=stock_analysis`（或等价问股路由） | |
| 1.2 | 工具命中 | Trace → `tool_call` → `tool_result` 含 **`valuation_profile_lookup`** | |
| 1.3 | 实时估值 | `valuation` 含现价、PE TTM、PB、市值；`as_of` 为「实时行情」 | |
| 1.4 | 历史结构 | `valuation_history.found=true`，含 `pe_ttm` / `pb` 的 **percentile** 或 **p25/p50/p75** | |
| 1.5 | 数据来源 | `valuation_history.data_origin=eastmoney_valuation_history`；`lookback_years` ≈ 3 | |
| 1.6 | 正文解读 | 正文 **不仅** 报单点 PE，须提及历史分位/与中位数对比等「贵不贵」语境 | |
| 1.7 | 参考来源 | `### 参考来源` 含腾讯行情 + 东财历史估值口径说明 | |

---

## 2. 综合基本面：估值与财报并存

**提问**：

> 长春高新基本面怎么样？

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 2.1 | 双工具 | Trace `tool_result` 同时含 `mock_financial_profile_lookup` 与 `valuation_profile_lookup` | |
| 2.2 | 历史估值 | `valuation_profile_lookup.valuation_history` 非空且 `found=true` | |
| 2.3 | 正文结构 | 有财务多期解读 + 估值历史语境，非仅实时 PE 一句带过 | |

---

## 3. 失败透明（历史接口异常时）

若东财历史接口暂时不可用（可断网模拟或看 Trace）：

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 3.1 | 实时仍可用 | `valuation` 仍可从腾讯返回（`found=true`） | |
| 3.2 | 历史降级 | `valuation_history` 为 `null` 或 `found=false`，`notes` 说明历史暂不可用 | |
| 3.3 | 不编造 | 正文 **不得** 编造历史分位数 | |

---

## 4. 非 Mock 口径

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 4.1 | 无演示标注 | 全文与 Trace **不得** 标注「演示/模拟估值」 | |
| 4.2 | `is_mock` | `valuation_profile_lookup.is_mock=false` | |

---

**全部通过后请回复**：「估值 P1 验收通过」——将更新 `tool-richness-roadmap.md` §一 T-021 → P1 ✅，并记录 `.sdd/status.json` 与验收结果文件。

**✅ 用户已于 2026-06-19 确认通过**（见 `acceptance-roadmap-T-021-P1-result.md`）。

**T-021 backlog（不阻塞 T-022）**：P2 同行估值对比、P3 `full_valuation` 一致预期 EPS/PEG。
