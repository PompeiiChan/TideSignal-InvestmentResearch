# Bad Case 总结

记录投研问答链路中已发现的用户可见严重错误、根因、修复方式与验收状态。

---

## BC-001 宁德时代总资产被写成「十几亿」

| 字段 | 内容 |
|------|------|
| **发现时间** | 2026-06-12 |
| **用户问题类型** | 个股基本面 / 资产规模（如「宁德时代基本面怎么样」） |
| **现象** | 回答中出现严重事实错误：宁德时代为万亿级龙头，但回复称总资产仅约「十几亿」量级 |
| **状态** | **已修复**（代码与单测；需重建 RAG 索引 v7 后线上生效） |

### 根因分析

1. **知识库单位换算错误（主因）**  
   - 一季报主要指标行：`总资产（千元） 1,046,329,036 …`  
   - `convert_financial_yuan_to_yi` 仅识别 `单位：千元` 表头，未识别字段名内联的 `（千元）`。  
   - 误将「千元」数值按「元」换算 → 索引块中出现 `总资产（千元） 10.46亿元`（应为约 **10463 亿元 / 1.05 万亿**）。

2. **财报召回加权不足（次因）**  
   - `is_financial_query()` 未包含「基本面」「总资产」等词。  
   - 问「宁德时代基本面怎么样」时 top6 全为研报、**0 条 financial**，模型缺少权威资产负债表片段。

3. **质检未拦截（伴生）**  
   - T-011a 后质检仅检查与 `rag_citations` 自洽；若 RAG 片段本身为错误换算值，质检仍可能 PASS。（本 Bad Case 未在本轮改质检规则。）

### 修复方式

| # | 改动 | 文件 |
|---|------|------|
| 1 | 行内 `（千元）/（万元）/（元）` 字段标签参与单位乘数 | `backend/src/services/rag/financial_units.py` |
| 1b | Q1 资产负债表等无 `单位：千元` 表头时，对整数型大额科目行推断千元口径 | `backend/src/services/rag/financial_units.py` |
| 2 | 扩展财报类查询词：基本面、总资产、资产规模、净资产、市值等 | `backend/src/services/rag/retriever.py` |
| 3 | 切块内容变更 → `RAG_INDEX_VERSION` 6 → **7** | `backend/src/services/rag/chunker.py` |
| 4 | 单测：一季报总资产换算、切块不含 `10.46亿元`、基本面触发 financial 查询 | `backend/tests/test_financial_units.py`、`backend/tests/test_rag_service.py` |

### 验收

- [x] `pytest backend/tests/test_financial_units.py` 17 项通过（含行内千元、无表头 `资产总计` 推断）
- [x] `pytest backend/tests/test_rag_service.py` 相关用例通过（切块后 `总资产（千元） 10463.29亿元`，无 `资产总计 10.46亿元`）
- [ ] **用户侧**：重建知识库索引后，问「宁德时代2026一季报总资产」或「宁德时代基本面」应不再出现 `10.46亿元` 级总资产；「资产规模」类问题应能召到 `financial` 且 `资产总计 9748.28亿元` 等正确口径

### 索引重建说明

代码合并后需触发全量索引重建（版本 v7）：

```bash
# 项目根目录；确保 Embedding 已配置
cd Projects_Repo/smart-investment-research
PYTHONPATH=. .venv/bin/python -c "
import asyncio
from backend.src.services.rag.service import RagService
async def main():
    s = RagService()
    await s.ensure_index(force=True)
    print('index ready', s.has_index())
asyncio.run(main())
"
```

或重启后端后首次提问触发构建（耗时数分钟）。构建完成前检索仍可能命中 v6 错误切块。

### 后续建议（未纳入本轮）

- 质检增加「龙头公司量级」常识校验（总资产 &lt; 1000 亿且与另一 RAG 口径差 100 倍以上 → FAIL）
- T-012 个股 agent 从 RAG 结构化抽取关键指标再生成，减少纯 Markdown 自由发挥
