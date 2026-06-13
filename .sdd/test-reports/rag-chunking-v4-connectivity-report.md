# 测试报告：RAG 切块 v4 连通性专项验证

**测试时间**：2026-06-12 09:52 CST  
**Tester Agent ID**：tester-subagent  
**验证范围**：RAG_INDEX_VERSION=4 切块逻辑与后端连通性（非 T-010/T-011 全量复验）

## 结果：FAIL

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 三类专用切块策略文件存在且 chunker 路由正确 | PASS | `chunk_strategies.py` 含 hotspots/financials/report/structured 策略；`chunker.py` 按文件夹路由；`RAG_INDEX_VERSION=4`；`bm25.py`、`retriever.py`、`service.py` 均存在 |
| 2 | hotspots 切块产出 breadcrumb + parent_text | PASS | `2026-06-market-hotspots.md` 产出 44 chunks，全部含 breadcrumb 与 parent_text；样例 breadcrumb 含「热点主线」 |
| 3 | financials 产出整表 chunk + NL summary | PASS | `000568-luzhoulaojiao-financial-2025A-2026Q1.md` 产出 146 chunks；含 6 个资产负债表类 chunk、2 个 summary（业绩摘要） |
| 4 | `test_rag_service.py` 全绿 | PASS | `10 passed, 6 skipped`（REAL_API_TEST 跳过用例正常 skip） |
| 5 | RagService.ensure_index + retrieve 代码路径可执行（有 Key 时真实命中） | FAIL | Embedding 已配置，单条 query embed 成功；但 `ensure_index(force=True)` 在 chunk 260 处因 91,347 字符超大文本触发上游 400，索引构建中断；`retrieve()` 降级为 mock、0 hits |
| 6 | 无密钥泄露、无语法错误 | PASS | `backend/src/services/rag/` 无硬编码 Key；单元测试与冒烟脚本无语法错误；`.env` 仅报告「已配置」 |

## 验证证据

### 1. 代码存在性抽检

| 文件 | 状态 | 关键证据 |
|------|------|----------|
| `backend/src/services/rag/chunk_strategies.py` | 存在 | `chunk_hotspot_file` / `chunk_financial_file` / `chunk_report_file` / `chunk_structured_file` |
| `backend/src/services/rag/chunker.py` | 存在 | `RAG_INDEX_VERSION = 4`（第 28 行）；路由 hotspots→financials→reports→structured |
| `backend/src/services/rag/bm25.py` | 存在 | `Bm25Index.from_chunks` |
| `backend/src/services/rag/retriever.py` | 存在 | `search_chunks` hybrid 检索 |
| `backend/src/services/rag/service.py` | 存在 | `ensure_index` / `retrieve` 使用 v4 切块与 embed |

### 2. 切块逻辑冒烟（PYTHONPATH=. .venv/bin/python）

```
Hotspots: 44 chunks, breadcrumb=44, parent_text=44
Financials (000568): 146 chunks, balance_sheet=6, NL/summary=2
Company report (300750): 78 chunks, forecast=5
chunk_knowledge_base indexable: 1772
RAG_INDEX_VERSION=4
```

financials 样例：
- summary breadcrumb: `泸州老窖2025年年度报告 > 业绩摘要`
- table breadcrumb: `泸州老窖2025年年度报告 > 第八节 财务报告 > 合并资产负债表`

### 3. 单元测试

```bash
cd Projects_Repo/smart-investment-research
PYTHONPATH=. .venv/bin/pytest backend/tests/test_rag_service.py -q
# 结果: 10 passed, 6 skipped, 6 warnings in 0.61s
```

### 4. Embedding 配置与连通性

| 检查项 | 结果 |
|--------|------|
| `backend/.env` Embedding 配置 | **已配置**（EMBEDDING_API_KEY / BASE_URL / MODEL / DIM 均非空） |
| 单条 query embedding | PASS（dim=4096） |
| `ensure_index(force=True)` v4 重建 | **FAIL** — 嵌入至 260/1772 后上游返回 400 |
| `retrieve()` 三条查询 | **FAIL** — 因索引未完成，全部 `mode=mock`、`hits=0` |

**失败根因 chunk**（首个触发 400 的切块）：

| 字段 | 值 |
|------|-----|
| chunk_id | `ann_000568_2025_stmt_007` |
| path | `financials/000568-luzhoulaojiao-financial-2025A-2026Q1.md` |
| section_title | 合并现金流量表 |
| embed_text 长度 | **91,347 字符** |
| 位置 | `chunk_knowledge_base()` 输出第 260 条（0-based） |

**同类超大切块扫描**（`embed_text` > 8000 字符，共 7 条）：

| 字符数 | chunk_id | section_title |
|--------|----------|---------------|
| 105,406 | ann_603288_2025_stmt_006 | 母公司现金流量表 |
| 100,837 | ann_300750_2025_stmt_005 | 母公司现金流量表 |
| 96,564 | ann_688256_2025_stmt_005 | 母公司现金流量表 |
| 95,512 | ann_002293_2025_stmt_006 | 合并利润表 |
| 91,347 | ann_000568_2025_stmt_007 | 合并现金流量表 |
| 16,316 | ann_002293_2025_stmt_005 | 母公司现金流量表 |
| 12,897 | ann_000568_2025_stmt_005 | 母公司现金流量表 |

索引磁盘状态（测试后）：
- `index_meta.json`: version=4, chunk_count=260, total_expected=1772, build_in_progress=true
- 原 v3 完整索引已被 force 重建清除，当前为不完整 v4 部分索引

### 5. API 层抽检（端口 8199，短时启动后关闭）

```
GET /api/health → 200 {"status":"ok","service":"smart-investment-research-api",...}
GET /api/data-sources/status → 200
  rag: {"mode":"mock","embedding_provider":"siliconflow-qwen","rerank_provider":"siliconflow-qwen","status":"mocked"}
```

API 服务可启动，RAG 状态正确反映索引未就绪（mocked）。

## 如果 FAIL，详情如下

### 问题 1：财务报表整表切块未限制 embed 文本长度，导致索引构建失败

- **标准**：#5 RagService.ensure_index + retrieve 有 Key 时真实命中
- **现象**：`ensure_index(force=True)` 在嵌入第 260 个 chunk 时，SiliconFlow Embedding API 返回 400（`code:20015, message: The parameter is invalid`）；同批次其余 3 条（3440/104/641 字符）单独嵌入均成功
- **位置**：`backend/src/services/rag/chunk_strategies.py`（`chunk_financial_file` 财务报表整表合并逻辑）；首个失败 chunk `ann_000568_2025_stmt_007`
- **建议修复方向**：对财务报表 statement 类 chunk 的 `embed_text`/`chunk_text` 增加最大长度约束（如 ≤8000 字符），超大表按行或按段二次切分；或在 `_embed_pending` 前校验并拒绝/拆分超长文本；修复后需重新 `ensure_index(force=True)` 验证全量 1772 chunks 可完成嵌入

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|-------------|
| 1 | force 重建中断后磁盘索引为 v4 部分状态（260/1772），影响后续真实检索 | RAG index_store | 修复切块后重新 force 重建；或从备份恢复 v3 索引作临时回退 |
| 2 | 端口 8099 被占用，Tester 改用 8199 完成 API 抽检 | 环境 | 确认是否有遗留 uvicorn 进程 |

## 系统级经验

- **类型**：重复
- **问题摘要**：财务报表整表合并切块未校验 embed 文本上限，导致 Embedding API 400 中断索引构建
- **影响范围**：所有使用本地知识库 RAG 且含大型财务报表的项目
- **建议规则**：切块策略产出 `embed_text` 前必须断言长度 ≤ Embedding 上游限制（建议 8000 字符）；单元测试应扫描全库 `chunk_knowledge_base()` 输出并断言无超长 chunk
