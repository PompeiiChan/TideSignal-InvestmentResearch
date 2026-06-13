# 工具数据丰富度路线图

> **维护说明**：每完成一个 Phase 的验收，将「当前活动 Phase」推进到下一项，并在 `.sdd/status.json` 的 `notes` 同步。  
> **对话提醒约定**：用户说「继续工具路线图」「按 roadmap 修」或「问数验收过了」时，Agent 应读本文件 **§二 当前活动 Phase** 并执行下一项，无需用户重复列举 backlog。

**最后更新**：2026-06-13  
**背景**：全链路工具审计结论——多数工具只返回「最新截面 / 单次调用」，与用户期望的「更丰富、可对比」不一致。财报多期（问股）已做第一轮修复；本路线图覆盖其余链路。

---

## 一、进度总览

| Phase | 名称 | 链路 | 状态 | 验收人 |
|-------|------|------|------|--------|
| **T-020** | 问数工具丰富度 | 问数 `data_query` | 🟡 **进行中** | 待用户 |
| **T-021** | 估值工具丰富度 | 问股 `valuation_profile_lookup` | ⏳ 待 T-020 验收后 | — |
| **T-022** | 问股财报深化 | 问股 `mock_financial_profile_lookup` + RAG | ⏳ 待 T-021 验收后 | — |
| **T-023** | 热点工具丰富度 | 热点 `hotspot_*` + RAG | ⏳ 待 T-022 验收后 | — |
| **T-024** | 离线 KB 与入库扩展 | 脚本 `ingest_*` + financials | ⏳ 待 T-023 验收后 | — |

---

## 二、当前活动 Phase：T-020 问数工具丰富度

### 2.1 问题摘要（审计结论）

| 问题 | 现状 | 用户体感 |
|------|------|----------|
| 编排写死 | `routing_decision` 三选一：排行 / 热力图 / 计算器 | 「既要热力图又要板块涨幅」只能得到一个 |
| 时间维度假参数 | `time_range` 槽位透传但 API 未使用 | 问「近一周」仍只有当日 |
| 榜单过短 | 默认 `rank_limit=5` | 信息量少 |
| 能力缺口 | 无指数点位、单股报价、跨日区间 | Prompt 已写「不支持」，但用户仍会问 |

### 2.2 实施分期（T-020 内部）

| 子阶段 | 内容 | 状态 |
|--------|------|------|
| **T-020-P1** | 动态 `tool_names` 编排（对齐问股方案 C）；支持一次调用排行+热力图；提高默认 `rank_limit` | 🟡 开发中 |
| **T-020-P2** | 指数 / 单股实时报价工具（东财或腾讯）；`index_quote_lookup` / `stock_quote_lookup` | ⏳ P1 验收后 |
| **T-020-P3** | `time_range` 真正接入（近 5/20 交易日涨跌幅、区间表现）；需新行情历史接口 | ⏳ P2 验收后 |

### 2.3 T-020-P1 技术要点

- 新增 `backend/src/agents/data_query_tool_plan.py`（白名单 + 兜底规则）
- `data_query_agent` JSON 增加 `tool_names`
- `routing_decision`：`data_query_agent` 默认 `tool_names: []`、`tool_plan_mode: agent`
- **保留硬规则**：槽位齐全时仍优先 `local_return_calculator`（独占，不走多工具）
- `tool_call`：在 `route_target == data_query_agent` 时解析 `agent_tool_names`
- Prompt：`data_query.py` 补充工具编排表与多工具示例

### 2.4 T-020 验收标准（用户门禁）

在 `VITE_USE_MOCK=false`、后端 8099 下实测：

1. **多工具**：问「今天行业热力图怎么样，顺便看看半导体成分股涨幅前五」→ Trace `tool_call` 命中 **≥2** 个工具（`sector_heatmap_lookup` + `market_ranking_lookup`），且前端有热力图块 + 正文解读。
2. **动态单工具**：问「全行业板块涨幅榜」→ 仅 `market_ranking_lookup`，`ranking_mode=industry_boards`。
3. **计算器独占**：给齐买卖价/份额 → 仅 `local_return_calculator`，不混调排行。
4. **榜单长度**：默认 `rank_limit` ≥ 8（或 Agent 显式规划 ≥8）。
5. **降级透明**：API 失败时 `fallback_used=true`，正文/Trace 标明 demo 口径。

**通过后**：将本文 §一 中 T-020 标为 ✅，§二 切换为 **T-021**，并更新 `.sdd/status.json`。

---

## 三、T-021 估值工具丰富度（T-020 验收后执行）

### 问题

`valuation_profile_lookup` 仅腾讯实时一帧（PE/PB/市值），无历史分位、同行对比、前瞻 PE。

### 目标

| 子项 | 内容 |
|------|------|
| P1 | 扩展为 `valuation` + `valuation_history`（近 3 年 PE/PB 序列或分位，数据源腾讯/东财） |
| P2 | 同行估值对比（同行业 3–5 家 PE/PB 表） |
| P3 | 接入 `third_party/a-stock-data` 的 `full_valuation`（机构一致预期 EPS、PEG） |

### 验收标准

- 问「长春高新估值贵不贵」→ 正文含 **当前估值 + 至少一项历史/同行上下文**（非单点 PE）。
- Trace 可见估值工具返回多字段结构，非仅 `as_of: 实时行情`。

---

## 四、T-022 问股财报深化（T-021 验收后执行）

### 问题

多期 `periods[]` 已上线，但仍缺：内置样本单期、KB 入库仅 2 期、缺现金流/负债、缺连续季报序列、RAG 偏最新 Q1。

### 目标

| 子项 | 内容 |
|------|------|
| P1 | 运行期财报工具带出现金流、资产负债等（与入库脚本字段对齐） |
| P2 | RAG 问股检索：同 `company_id` 按 `time_period` 去重，保证多期 chunk 进 evidence |
| P3 | `ingest_chinext_sina_financials.py` 扩展为 3 年年报 + 多季报写入 KB |

### 验收标准

- 已入库标的：工具 `periods.length` ≥ 3 或 RAG 补全缺失期。
- 正文多期表含 **营收、利润、毛利率、ROE** 且至少一项 **现金流或负债** 指标（有数据时）。

---

## 五、T-023 热点工具丰富度（T-022 验收后执行）

### 问题

信号仅当日 THS；公告依赖用户带 `stock_codes`；快讯最多 8 条；编排固定双工具无法按场景裁剪。

### 目标

| 子项 | 内容 |
|------|------|
| P1 | 从 query/slots 自动解析股票代码拉巨潮公告 |
| P2 | 热点动态 `tool_names`（复盘类可跳过当日信号） |
| P3 | RAG `hotspot_dual` 按月份多路检索，支撑「热点演变」叙述 |

### 验收标准

- 问「机器人板块最近为什么火」→ 含 RAG 月报 + 事实层快讯/公告（若有代码则含公告）。
- 问「帮我复盘 4 月到 6 月半导体热点」→ 命中多个月报片段或明确标注证据不足。

---

## 六、T-024 离线 KB 与入库扩展（T-023 验收后执行）

- 全市场财报 KB：3 年年报 + 最新季报批量入库
- 与 T-022-P3 联动，验收以 KB 文件 `### 主要财务数据` 段数量为准

---

## 七、相关文件索引

| 用途 | 路径 |
|------|------|
| 本路线图 | `docs/agent/tool-richness-roadmap.md` |
| 问股动态编排（参考实现） | `backend/src/agents/stock_tool_plan.py` |
| 问数编排（T-020） | `backend/src/agents/data_query_tool_plan.py` |
| 路由默认计划 | `backend/src/agents/nodes/routing_decision.py` |
| 问数 Agent Prompt | `backend/src/integrations/llm/prompts/agents/data_query.py` |
| 项目状态指针 | `.sdd/status.json` |
| 开发总计划 | `docs/Plan.md` |

---

## 八、给 Agent 的续作指令（复制即用）

```text
请读取 docs/agent/tool-richness-roadmap.md 的「当前活动 Phase」，从第一个未完成的子阶段开始实现；完成后更新路线图状态与 .sdd/status.json，并列出验收步骤给用户。
```
