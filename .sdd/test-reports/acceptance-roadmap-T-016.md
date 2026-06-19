# 用户验收清单：T-016 会话 pending_slots 多轮闭环（F19）

**前置**：后端 `8099`、前端 `5199`，`VITE_USE_MOCK=false`，`LANGGRAPH_ENV=local`  
**依赖**：T-015 短期记忆已验收（`history_summary` 可用）

> **BC-008 修复目标**：「宁德时代基本面」→「一季报呢」不再因缺失 `stock_name` 触发澄清。

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

> 若本地已有其他实例占用端口，可临时使用用户门禁端口：后端 `8003`、前端 `5175`，并设置 `VITE_BACKEND_PROXY_TARGET=http://localhost:8003`。

---

## 1. 续问继承（BC-008 主路径）

在同一**新会话**中连续提问：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 1 | 宁德时代基本面怎么样 | 正常个股分析回答（非澄清追问公司名） | |
| 2 | 一季报呢 | **延续宁德时代语境**回答一季报；**不得**出现「请提供股票名称/代码」类澄清 | |

**可选等价续问**（任选其一验证 AC1）：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 2′ | 它 2026 一季报怎么样 | 同上：含宁德时代语境的一季报分析 | |

---

## 2. 显式换标的（覆盖继承）

在**同一新会话**中：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 1 | 宁德时代基本面怎么样 | 回答围绕宁德时代 | |
| 2 | 泸州老窖呢 | 回答围绕**泸州老窖**，**不得**仍引用宁德时代作为分析主体 | |

---

## 3. Trace 检查（P04 管理端）

打开 **第 2 轮「一季报呢」** 的 Trace：

### 3.1 `slot_extraction` 步骤

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 3.1.1 | `input.pending_slots` | 含 `stock_name: 宁德时代`（或等价 `stock_code`） | |
| 3.1.2 | `input.history_summary` | 非空，含上轮宁德时代对话摘要 | |
| 3.1.3 | `output.extracted_slots` | 本轮新抽槽位（如 `time_range` / `analysis_dimension`），**可无** `stock_name` | |
| 3.1.4 | `output.slots` / `output.active_slots` | **含** `stock_name=宁德时代` | |
| 3.1.5 | `output.inherited_slot_keys` | 含 `stock_name`（及可能的 `stock_code`） | |
| 3.1.6 | `output.missing_slots` | **不含** `stock_name` | |

### 3.2 `clarification_check` 步骤

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 3.2.1 | `input.inherited_slot_keys` | 含 `stock_name` | |
| 3.2.2 | `output.need_clarification` | `false` | |
| 3.2.3 | `output.clarification_reason` | 不含「核心槽位缺失：stock_name」 | |

### 3.3 换标的 Trace（第 2 轮「泸州老窖呢」）

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 3.3.1 | `slot_extraction.output.overridden_slot_keys` | 含 `stock_name` | |
| 3.3.2 | `slot_extraction.output.slots.stock_name` | `泸州老窖` | |

---

## 4. 真缺槽仍澄清（回归）

在新会话中**直接**提问（无上一轮标的）：

| 轮次 | 输入 | 期望 | 通过 □ |
|------|------|------|--------|
| 1 | 一季报怎么样 | 触发澄清，追问股票名称或代码 | |

Trace：`clarification_check.output.need_clarification` = `true`，原因含 `stock_name`。

---

## 5. 回归确认

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 5.1 | 首轮单轮问股 | 与 T-013 行为一致，无退化 | |
| 5.2 | T-015 短期记忆 | 第 6 轮仍仅保留 5 轮 QA 窗口 | |
| 5.3 | Trace 时间线 | `context_preprocess` → `intent_recognition` → `slot_extraction` → `clarification_check` 正常展示 | |

---

**通过后请回复**：「T-016 pending_slots 验收通过」或指出未通过条目编号。

**用户门禁端口说明**：本清单默认 Agent 自动验证端口（后端 `8099`、前端 `5199`）。若需与本地其他实例隔离，可临时设置 `VITE_BACKEND_PROXY_TARGET=http://localhost:8003` 并将后端改监听 `8003`、前端 `5175`。
