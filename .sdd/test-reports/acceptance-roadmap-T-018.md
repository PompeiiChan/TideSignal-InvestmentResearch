# 用户验收清单：T-018 问股 live 基本面 Tool

**前置**：后端 `8099`、前端 `5199`，`VITE_USE_MOCK=false`，`LANGGRAPH_ENV=local`  
**依赖**：T-013 V1.1 真实 AI 全链路已验收

> **验收目标**：问股链路能调用新浪/同花顺/东财 live Tool，管理端 Trace 可见工具归因；fallback 不得伪装 live。

---

## 0. 启动服务

**终端 1 — 后端**

```bash
cd Projects_Repo/smart-investment-research/backend
PYTHONPATH=.. ../.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8099
```

**终端 2 — 前端**

```bash
cd Projects_Repo/smart-investment-research/frontend
VITE_USE_MOCK=false npm run dev -- --host 127.0.0.1 --port 5199
```

浏览器打开：`http://127.0.0.1:5199`

> 用户门禁端口：后端 `8003`、前端 `5175`，设置 `VITE_BACKEND_PROXY_TARGET=http://localhost:8003`。

---

## 1. 数据说明页 — live 数据源可观测

打开 **数据说明页（P05）**：

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 1.1 | 列表含 live 条目 | 可见「新浪财经财报 API」「同花顺一致预期」「东财研报 reportapi」等 live 类型 | |
| 1.2 | 状态 | 显示 `ready` 或 `degraded`，**不展示任何 API Key** | |
| 1.3 | 与 KB 并存 | 原有 financial/report/knowledge 本地条目仍在 | |

**可选 curl 对照**：

```bash
curl -s http://127.0.0.1:8099/api/data-sources/status | jq '.data.mock_data[] | select(.type|test("live")) | {type,name,status}'
```

---

## 2. 未收录 A 股基本面（新浪 live）

在客户端 **新建会话**，输入 KB 外创业板代码（示例）：

| # | 输入 | 期望 | 通过 □ |
|---|------|------|--------|
| 2.1 | `301001 凯淳股份基本面怎么样` | 回答含营收/净利润/毛利率或 ROE 等关键指标，并标明报告期（如 2025 年报、2026Q1） | |
| 2.2 | 来源口径 | 正文或引用注明新浪公开 API 或本地 KB；**不得空编数字** | |

---

## 3. 机构观点（一致预期 + 研报元数据）

新建会话：

| # | 输入 | 期望 | 通过 □ |
|---|------|------|--------|
| 3.1 | `机构怎么看宁德时代` | 回答含机构一致预期情景 **或** 卖方研报列表（评级、EPS 预测等），**非空** | |
| 3.2 | 观点边界 | 机构观点表述为「观点非事实」，含风险提示 | |

---

## 4. 管理端 Trace — tool_call 归因（P04）

对 **§3 机构怎么看宁德时代** 本轮问答，打开右侧 Trace → 点击 **`tool_call`** 节点：

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 4.1 | 工具名称 | 可见 `consensus_valuation_lookup`、`research_report_metadata_lookup`（及财务 Tool） | |
| 4.2 | 归因区块 | 展开含「工具归因」：`data_origin`、`fallback` 状态 | |
| 4.3 | Apache 许可 | 含 `third_party/a-stock-data (Apache-2.0)` | |
| 4.4 | live vs fallback | THS/东财 live 时 `fallback=false`；KB 缓存时 `fallback=true` 且 origin 为 local_*，**不得把 fallback 当 live** | |

点击 **查看完整 JSON**，确认 `tool_attributions` 数组非空。

---

## 5. PRD 边界（负向）

| # | 输入 | 期望 | 通过 □ |
|---|------|------|--------|
| 5.1 | `宁德时代今日盘口怎么样` | 不走 live 基本面财报主路径；回答说明不支持 K 线/盘口类 | |
| 5.2 | 估值口径 | 综合基本面仅 PE/PB/市值等，不出现短线资金流指标 | |

---

## 6. 降级边界（可选）

断网或外部 API 不可用时（若可模拟）：

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 6.1 | HTTP 状态 | 提问仍返回 200，**不 500** | |
| 6.2 | 正文 | 明确说明暂无结构化 live 数据或已降级 KB | |
| 6.3 | Trace | `fallback_used=true` 且 origin 非 live API | |

---

## 验收签字

| 项目 | 结果 |
|------|------|
| 总体结论 | □ 通过　□ 不通过 |
| 备注 | |
| 验收人 / 日期 | |

**技术报告**：`.sdd/test-reports/test-T-018.md`
