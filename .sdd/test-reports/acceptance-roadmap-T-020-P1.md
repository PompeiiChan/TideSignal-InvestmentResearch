# 用户验收清单：路线图 T-020-P1 问数工具丰富度

**版本检查点**：`7485f74`（V1.2 checkpoint）  
**验收环境**：`VITE_USE_MOCK=false` · 后端 **8099** · 前端 **5199** · `LANGGRAPH_ENV=local`  
**参考**：`docs/agent/tool-richness-roadmap.md` §2.4（第 5 条已按「去 Mock」更新）

---

## 0. 验收前准备

| # | 检查项 | 操作 | 通过 □ |
|---|--------|------|--------|
| 0.1 | 后端就绪 | `curl -s http://127.0.0.1:8099/api/health` 返回 `status: ok` | |
| 0.2 | 前端联调 | 浏览器打开 http://127.0.0.1:5199 ，`frontend/.env` 为 `VITE_USE_MOCK=false` | |
| 0.3 | LangGraph | `GET /api/config/status` → `orchestration.status` 为 `ready` | |
| 0.4 | 管理端 Trace | 客户端提问后切到 **管理端**，右侧 **Trace 链路** 可展开 `tool_call` 节点 | |
| 0.5 | 网络 | 本机可访问东财 push2（问数排行/热力图依赖外网；失败时应见空结果+说明，**不得**出现寒武纪/宁德时代等 demo 价） | |

**自动化预检（可选）**：

```bash
cd backend && PYTHONPATH=.. ../.venv/bin/python -m pytest \
  tests/test_data_query_tool_plan.py \
  tests/test_market_ranking_lookup.py \
  tests/test_sector_heatmap.py \
  tests/test_heatmap_routing.py -q
```

---

## 1. 多工具：热力图 + 板块成分股排行

**提问（建议新建会话）**：

> 今天行业热力图怎么样，顺便看看半导体成分股涨幅前五

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 1.1 | 意图路由 | Trace：`intent_id=data_query`，`route_target=data_query_agent` | |
| 1.2 | 工具数量 | Trace → `tool_call` → `tool_result` 同时含 **`sector_heatmap_lookup`** 与 **`market_ranking_lookup`** | |
| 1.3 | 热力图数据 | `sector_heatmap_lookup.is_mock=false`，`tile_count` ≥ 5 | |
| 1.4 | 排行数据 | `market_ranking_lookup.ranking_mode=board_stocks`，`industry` 含「半导体」，`row_count` ≥ 5 | |
| 1.5 | 前端富组件 | 回答下方有 **行业板块热力图** 交互块；正文解读排行要点（不必重复整张表） | |
| 1.6 | 过程时间线 | 流式开始后过程区折叠为「▸ 执行过程…」，可点开回看 | |
| 1.7 | 非 Mock | 全文与参考来源 **不得** 标注「演示/模拟行情」；数据来源为东财 push2 | |

---

## 2. 动态单工具：全行业板块涨幅榜

**提问**：

> 全行业板块涨幅榜

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 2.1 | 工具唯一 | Trace `tool_call` **仅** `market_ranking_lookup`（无 `sector_heatmap_lookup`） | |
| 2.2 | 排行模式 | `ranking_mode=industry_boards`，`industry` 为「全行业」或等价文案 | |
| 2.3 | 行含义 | 排行表中 `stock_name` 列为 **板块名**（非个股代码） | |
| 2.4 | 富组件 | 有 **行情排行** 表（`ranking_table`） | |
| 2.5 | 榜单长度 | `row_count` ≥ **8**（`tool_call` 默认 `rank_limit=10`） | |

---

## 3. 计算器独占：不混调排行/热力图

**提问（示例参数可改）**：

> 帮我算一下：买入价 10 元，卖出价 12 元，1000 股，手续费万三

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 3.1 | 工具独占 | Trace `tool_call` **仅** `local_return_calculator` | |
| 3.2 | 无行情工具 | `tool_result` 中 **无** `market_ranking_lookup` / `sector_heatmap_lookup` | |
| 3.3 | 富组件 | 有 **收益率测算**（`calculator`）交互块，含净收益/收益率 | |
| 3.4 | 合规 | 正文含风险提示，无买卖建议 | |

---

## 4. 榜单默认长度

可在 **用例 2** 一并确认，或单独问：

> 半导体板块涨幅前十

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 4.1 | rank_limit | Trace 中 `tool_params.rank_limit` ≥ **8**（默认 10） | |
| 4.2 | 表行数 | 前端排行表可见行数 ≥ **8**（API 正常时） | |

---

## 5. API 失败透明（去 Mock 后）

> 本项仅在东财接口不可用时抽检；正常网络下可跳过。

**模拟方式（可选）**：断网或临时阻断 `push2.eastmoney.com` 后提问「全行业板块涨幅榜」。

| # | 验收点 | 期望 | 通过 □ |
|---|--------|------|--------|
| 5.1 | 无假数据 | **不得** 返回寒武纪/宁德时代等内置 demo 价 | |
| 5.2 | 空结果 | `row_count=0` 或 `tile_count=0`，`is_mock=false` | |
| 5.3 | 正文诚实 | 明确说明行情接口暂不可用或暂无数据，不编造涨跌幅 | |
| 5.4 | Trace | `tool_result` 含 `error` 或 `notes` 说明失败原因 | |

---

## 6. 验收结论

| 项 | 填写 |
|----|------|
| 验收日期 | |
| 验收人 | |
| 总体结论 | □ 通过　□ 不通过 |
| 失败用例编号 | |
| 备注 | |

**全部通过后请回复**：「问数 P1 验收通过」——将更新 `tool-richness-roadmap.md` §一 T-020 → ✅，§二 切换至 **T-021**，并记录 `.sdd/status.json`。

---

## 附录：Trace 快速定位

1. 管理端 → 选中对应会话 → 右侧 **Trace 链路**
2. 展开 **`tool_call`** 节点 → 查看 `raw_json.output.tool_result` 或 `tool_names`
3. 关键字段：
   - `market_ranking_lookup.ranking_mode`：`industry_boards` | `board_stocks`
   - `market_ranking_lookup.row_count` / `sector_heatmap_lookup.tile_count`
   - `is_mock` 应为 `false`（问数行情链路）
