# T-014-P2 Query 改写规则优化 + 按维度多 Query（F18 续）

> **任务 ID**：T-014-P2（T-014 Phase ① 修补 + 规则化 Phase ③）  
> **前置**：T-014 Phase ① 已落地（`query_rewrite` + `retrieval_query`）  
> **Bad Case**：「海天味业基本面」被收成「海天味业 财报」，过度收敛  
> **产出日期**：2026-06-20  
> **状态**：待 Developer 执行

---

## 1. 目标

### Step A — Phase ① 修补

1. **显性问句 passthrough**：原句含 `stock_name` + 分析维度（基本面/估值/风险…）→ 不改 `retrieval_query`
2. **去掉默认 append「财报」**：仅当用户/槽位明确指向季报、年报、业绩、营收时加财报类词
3. **收紧短句判定**：公司名 + 主题齐全 → 不算续问（避免 `海天味业基本面` 被当短句改写）
4. **续问保留**：`它一季报怎么样` + `stock_name` → 仍拼 `公司 + 期别`（可加财报词）

### Step B — 规则化多 Query（Phase ③ 子集）

5. 对 **宽维度问股**（基本面/估值/综合诊断）输出 `retrieval_queries[]`（2～4 条）
6. `rag_retrieval` 主路径：有 `retrieval_queries` 时走 `retrieve_targeted` 合并；否则单 `retrieval_query`
7. Trace 可见 `retrieval_query` + `retrieval_queries` + `rewrite_method`

### 非目标

- Phase ② LLM 改写
- `supplement_mode` / `gap_planner` 行为变更
- `stock_narrative_mode` 已有 `build_stock_narrative_rag_queries` 路径不重写

---

## 2. `retrieval_query.py` 重构

### 2.1 新常量

```python
_ANALYSIS_DIMENSION_KEYWORDS = re.compile(
    r"基本面|估值|风险|盈利能力|现金流|负债|毛利率|ROE|竞争力|业务结构|财报|年报|季报|一季报"
)
_FINANCIAL_PERIOD_KEYWORDS = re.compile(r"年报|季报|一季报|半年报|业绩|营收|利润|财报")
```

### 2.2 新辅助函数

```python
def _query_has_stock_and_dimension(query: str, stock_name: str) -> bool:
    """公司名 + 分析维度 → 显性问句，应 passthrough 主 query。"""

def _needs_follow_up_rewrite(query: str, stock_name: str) -> bool:
    """仅续问/指代/缺公司名时 True；显性完整问句 False。"""

def build_dimension_retrieval_queries(
    *,
    stock_name: str,
    dimension: str,
    time_range: str = "",
    normalized_query: str = "",
) -> list[str]:
    """按维度映射 2～4 条子 query，上限 MAX_DIMENSION_QUERIES=4。"""
```

### 2.3 维度映射表（规则）

| dimension / topic | 子 query 模板（`{name}` = stock_name） |
|-------------------|----------------------------------------|
| 基本面（默认宽问） | `{name} 财务 营收 利润 现金流 年报`；`{name} 盈利能力 ROE 毛利率`；`{name} 公司研报 竞争力 行业` |
| 估值 | `{name} 估值 PE PB 历史分位`；`{name} 市值 盈利预测` |
| 一季报/2026Q1 等 | `{name} {period} 财务`；可选 `{name} {period} 公告` |
| 风险 | `{name} 风险 负债 现金流 年报` |

`build_retrieval_query` 返回扩展为：

```python
@dataclass
class RetrievalQueryPlan:
    retrieval_query: str
    retrieval_queries: list[str]  # 空或 len==1 表示单路
    rewrite_method: RewriteMethod  # 新增 rule_dimension_split
    changed: bool
```

**RewriteMethod** 增加：`rule_dimension_split`

### 2.4 决策流（stock_analysis）

```
if _query_has_stock_and_dimension → retrieval_query = query (passthrough)
    if dimension in {基本面, 宽问} → retrieval_queries = build_dimension_...(基本面)
    rewrite_method = rule_dimension_split, changed = len(queries)>1 or query!=original

elif _needs_follow_up_rewrite → 现有 _build_stock_retrieval_query（无默认财报）
    retrieval_queries = []  # 单路

elif _query_already_rich → passthrough

else → passthrough 或轻量拼接
```

**删除/禁用**：

- `_build_stock_retrieval_query` 末尾无条件 `parts.append("财报")`
- `f"{stock_name} {dimension} 财报"` 分支（line 136-140）改为仅 period 场景加财报词

---

## 3. 节点与 RAG

### 3.1 `query_rewrite.py`

- 使用 `RetrievalQueryPlan`
- output / state：`retrieval_queries: list[str]`
- trace summary 含子 query 数量

### 3.2 `state.py`

```python
retrieval_queries: list[str]
```

### 3.3 `rag_retrieval.py` 主路径 `else` 分支

```python
extra_queries = state.get("retrieval_queries") or []
if len(extra_queries) >= 2:
    rag_result = await rag.retrieve_targeted(
        extra_queries,
        top_k=top_k,
        entity_name=stock_name,
    )
elif len(extra_queries) == 1:
    rag_result = await rag.retrieve(extra_queries[0], top_k=top_k)
else:
    rag_result = await rag.retrieve(effective_query, top_k=top_k)
```

- `input_data` 增加 `retrieval_queries`
- `stock_narrative_mode` / `hotspot_*` / `supplement_mode` **不变**

---

## 4. 文档

- `docs/agent/langgraph-flow.md` §7.1：`retrieval_queries[]`、P2 行为
- `docs/agent/response-bad-case.md`：BC-009 海天味业基本面过度收敛（已修）

---

## 5. 测试

### `test_retrieval_query.py` 新增/修改

| 用例 | 断言 |
|------|------|
| `test_haitian_fundamentals_passthrough` | `海天味业基本面` + stock_name → retrieval_query 原句，`财报` 不在主 query |
| `test_haitian_dimension_split` | retrieval_queries ≥ 2，含财务/研报等 |
| `test_follow_up_still_rewrites` | `它一季报怎么样` + 宁德时代 → 含公司+一季报 |
| `test_luolai_explicit_passthrough` | `罗莱生活 2026 年一季报` passthrough |
| 回归 prior tests | 仍 pass |

### `test_rag_retrieval_query.py`

- mock state 含 `retrieval_queries` len≥2 → `retrieve_targeted` 被调用

### `test_query_rewrite_node.py`

- output 含 `retrieval_queries` 字段

---

## 6. 验收标准（P2）

| # | 标准 |
|---|------|
| 1 | 「海天味业基本面」Trace：`retrieval_query` 保持语义，非「海天味业 财报」 |
| 2 | 同上 Trace：`retrieval_queries` ≥2 条，RAG 走 `retrieve_targeted` |
| 3 | 「它一季报怎么样」续问改写不退化 |
| 4 | Embedding 不可用：改写与多 query 不阻断 BM25 |

---

## 7. 收尾

- `.sdd/developer-reports/T-014-P2-completion.md`
- `.sdd/experience.md`
- Commit：`fix(T-014-P2): Query 改写 passthrough 与维度多路检索`
