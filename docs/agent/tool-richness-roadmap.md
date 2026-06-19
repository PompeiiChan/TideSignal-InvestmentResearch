# 工具数据丰富度路线图

> **维护说明**：每完成一个 Phase 的验收，将「当前活动 Phase」推进到下一项，并在 `.sdd/status.json` 的 `notes` 同步。  
> **对话提醒约定**：用户说「继续工具路线图」「按 roadmap 修」或「问数验收过了」时，Agent 应读本文件 **§二 当前活动 Phase** 并执行下一项，无需用户重复列举 backlog。

**最后更新**：2026-06-19  
**背景**：全链路工具审计结论——多数工具只返回「最新截面 / 单次调用」，与用户期望的「更丰富、可对比」不一致。财报多期（问股）已做第一轮修复；本路线图覆盖其余链路。

---

## 一、进度总览

| Phase | 名称 | 链路 | 状态 | 验收人 |
|-------|------|------|------|--------|
| **T-020** | 问数工具丰富度 | 问数 `data_query` | ✅ **P1 已验收**（P2/P3 待办） | 用户 2026-06-18 |
| **T-021** | 估值工具丰富度 | 问股 `valuation_profile_lookup` | ✅ **P1 已验收**（P2/P3 待办） | 用户 2026-06-19 |
| **T-022** | 问股财报深化 | 问股 `mock_financial_profile_lookup` + RAG | 🟡 **进行中** | 待用户 |
| **T-023** | 热点工具丰富度 | 热点 `hotspot_*` + RAG | ⏳ 待 T-022 验收后 | — |
| **T-024** | 离线 KB 与入库扩展 | 脚本 `ingest_*` + financials | ⏳ 待 T-023 验收后 | — |

---

## 二、当前活动 Phase：T-022 问股财报深化

> **T-021-P1** 已于 2026-06-19 用户验收通过（报告：`.sdd/test-reports/acceptance-roadmap-T-021-P1-result.md`）。  
> **T-021-P2/P3**（同行估值对比、一致预期 EPS/PEG）仍属估值 backlog，不阻塞 T-022。

### T-021 归档摘要（P1）

#### 2.1 问题摘要

`valuation_profile_lookup` 原先仅腾讯实时一帧（PE/PB/市值），无法回答「贵不贵」的历史语境。

#### 2.2 实施分期（T-021 内部）

| 子阶段 | 内容 | 状态 |
|--------|------|------|
| **T-021-P1** | `valuation` + `valuation_history`（近 3 年 PE/PB 分位，东财日频） | ✅ **已验收**（2026-06-19） |
| **T-021-P2** | 同行估值对比（同行业 3–5 家 PE/PB 表） | ⏳ backlog（估值） |
| **T-021-P3** | `full_valuation`（机构一致预期 EPS、PEG） | ⏳ P2 后 |

#### 2.3 T-021-P1 技术要点

- `backend/src/integrations/market_data/em_valuation_history_client.py`（东财 `RPT_VALUEANALYSIS_DET`）
- `valuation_profile_lookup` 叠加 `valuation_history`（分位 + `quarterly_series`）
- `assembly.py` / `stock_analysis.py` / `citation_catalog`：估值解读须结合历史分位

#### 2.4 T-021 验收标准（P1 用户门禁）

- 问「长春高新估值贵不贵」→ 正文含 **当前估值 + 历史分位/中位数语境**（非单点 PE）
- Trace `valuation_profile_lookup` 含 `valuation_history`（`data_origin=eastmoney_valuation_history`）

**用户验收清单**：`.sdd/test-reports/acceptance-roadmap-T-021-P1.md`  
**验收结果**：`.sdd/test-reports/acceptance-roadmap-T-021-P1-result.md`（用户 PASS，2026-06-19）

**通过后**：§一 T-021 标 P1 已验收；§二 切换 **T-022**（已完成）。

---

## 三、T-021 估值工具丰富度（归档）

> 当前活动 Phase 已切换至 **T-022**，本节保留完整规格供 P2/P3 backlog 参考。

### 问题

`valuation_profile_lookup` 仅腾讯实时一帧（PE/PB/市值），无历史分位、同行对比、前瞻 PE。

### 目标

| 子项 | 内容 | 状态 |
|------|------|------|
| P1 | 扩展为 `valuation` + `valuation_history`（近 3 年 PE/PB 序列或分位，数据源腾讯/东财） | ✅ **已验收**（2026-06-19） |
| P2 | 同行估值对比（同行业 3–5 家 PE/PB 表） | ⏳ backlog |
| P3 | 接入 `third_party/a-stock-data` 的 `full_valuation`（机构一致预期 EPS、PEG） | ⏳ backlog |

### P1 技术要点（2026-06-15）

- 新增 `backend/src/integrations/market_data/em_valuation_history_client.py`（东财 `RPT_VALUEANALYSIS_DET`）
- `valuation_profile_lookup` 在腾讯实时 `valuation` 基础上叠加 `valuation_history`（分位 + 季度序列）
- `assembly.py` / `stock_analysis.py`：估值解读须结合历史分位
- 用户验收清单：`.sdd/test-reports/acceptance-roadmap-T-021-P1.md`

### 验收标准

- 问「长春高新估值贵不贵」→ 正文含 **当前估值 + 至少一项历史/同行上下文**（非单点 PE）。
- Trace 可见估值工具返回多字段结构，非仅 `as_of: 实时行情`。

---

## 四、T-022 问股财报深化（当前执行）

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
