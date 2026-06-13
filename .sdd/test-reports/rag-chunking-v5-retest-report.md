# 测试报告：RAG 切块 v5 复验

**测试时间**：2026-06-12 10:57 CST  
**Tester Agent ID**：tester-subagent  
**验证范围**：RAG_INDEX_VERSION=5 报表 parent-child embed 修复复验（对照 v4 FAIL：财务报表整表 embed 超长）

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | RAG_INDEX_VERSION=5 + 报表 parent-child embed 修复存在 | PASS | `chunker.py:28` 为 `RAG_INDEX_VERSION = 5`；`chunk_strategies.py` 含 `_split_statement_for_embed`（353 行起），`_chunk_financial_statements` 按子块 embed（`embed_parts` 循环）且 `parent_text=merged` 保留整表 |
| 2 | max(embed_text) ≤ 1200 字符 | PASS | `chunk_knowledge_base()` 全量 2510 chunks，`max_embed_len=1101`，`chunks_over_1200=0`；v4 失败时存在 91,347 字符块，已消除 |
| 3 | hotspots / financials 冒烟 PASS | PASS | hotspots 137/137 含 breadcrumb + parent_text；000568 合并资产负债表 3 个 embed 子块、1 个 parent、parent_text 长 2302（整表）、含 2 个「业绩摘要」summary 块 |
| 4 | `test_rag_service.py` 全绿 | PASS | `10 passed, 6 skipped`（REAL_API_TEST 跳过用例正常 skip） |
| 5 | ensure_index + retrieve 真实命中（有 Key 时） | PASS | Embedding/Rerank 均已配置；磁盘索引 v5 完整（2510 chunks）跳过重建；三条查询均 `mode=hybrid`、`hits=6`、`embedding_connected=true`、`rerank_connected=true`，top hit 类型分别为 market / financial / report |
| 6 | 无密钥泄露 | PASS | 源码与 `.md`/`.json` 无硬编码 Key；报告仅写「已配置/未配置」，不输出 Key 原文 |

## 验证证据

### 1. 代码抽检

| 检查项 | 位置 | 证据 |
|--------|------|------|
| 索引版本 | `backend/src/services/rag/chunker.py:28` | `RAG_INDEX_VERSION = 5` |
| 子块拆分函数 | `backend/src/services/rag/chunk_strategies.py:353-379` | `_split_statement_for_embed` 按行拆分、重复表头、上限 `_CHILD_MAX_CHARS=900` |
| 报表切块 | `backend/src/services/rag/chunk_strategies.py:308-350` | `embed_parts = _split_statement_for_embed(merged, max_chars=_CHILD_MAX_CHARS)`；循环 `_make_chunk(..., body=part, parent_text=merged, chunk_role="child")` |
| 会计政策块 | `backend/src/services/rag/chunk_strategies.py:259-261` | 非 MDA 正文经 `_split_prose(section_body, max_chars=...)` 拆分；全库最大 embed 1101 ≤ 1200 |

### 2. 切块冒烟

**命令**（项目根目录，运行时：`PYTHONPATH=. .venv/bin/python`）：

```
RAG_INDEX_VERSION 5
total_chunks 2510
max_embed_len 1101
max_chunk_id ann_300750_2025_policy_002_001 type financial
chunks_over_1200 0
hotspots_count 137 with_breadcrumb 137 with_parent_text 137
f568_balance_sheet_chunks 3
max_embed_parts_per_parent 3
sample_parent_text_len 2302
sample_embed_len 953
sample_chunk_role child
f568_nl_summary_chunks 2 (业绩摘要 role=summary)
hotspot_smoke PASS
```

### 3. 单元测试

**命令**：`PYTHONPATH=. .venv/bin/pytest backend/tests/test_rag_service.py -q`

```
10 passed, 6 skipped, 6 warnings in 0.53s
```

### 4. 外部服务配置与连通性

| 配置项 | 状态 |
|--------|------|
| EMBEDDING_API_KEY | 已配置 |
| EMBEDDING_BASE_URL / MODEL | 已配置 |
| RERANK_API_KEY | 已配置 |
| RERANK_BASE_URL / MODEL | 已配置 |

**磁盘索引**（`data/knowledge-base/.index/index_meta.json`）：

- version: 5
- chunk_count: 2510
- build_in_progress: false
- built_at: 2026-06-12T02:04:43Z

**ensure_index**：跳过全量重建（v5 完整索引已存在）

**retrieve 三条查询**：

| 查询 | mode | hits | top source_type | top title（截断） | rerank_connected |
|------|------|------|-----------------|-------------------|------------------|
| 2026年6月 AI 硬件为什么跌 | hybrid | 6 | market | 2026 年 6 月 A股月度热点文档… | true |
| 泸州老窖2025年报营收 | hybrid | 6 | financial | 泸州老窖2025年年度报告 | true |
| 宁德时代研报盈利预测 | hybrid | 6 | report | 宁德时代公司研报：技术迭代引领… | true |

### 5. API 抽检（可选）

服务已在 `127.0.0.1:8099` 监听（`curl --noproxy '*'` 绕过本机 http_proxy）：

- `GET /api/health` → `status: ok`
- `GET /api/data-sources/status` → `rag.status: ready`，`rag.mode: semantic`

## 与 v4 FAIL 对比

| 维度 | v4（FAIL） | v5（PASS） |
|------|-----------|-----------|
| 索引版本 | 4 | 5 |
| 全库 indexable chunks | 1772 | 2510 |
| max(embed_text) | 91,347（整表直嵌） | 1101 |
| ensure_index | 第 260 chunk 触发 Embedding 400 | 磁盘索引完整，无需重建 |
| retrieve | mock / 0 hits | hybrid / 6 hits × 3 查询 |

## 运行时说明

- 用户指定 `backend/.venv/bin/python`；`backend/.venv` 为本轮新建但未完成依赖安装。
- 实际使用项目根 `Projects_Repo/smart-investment-research/.venv/bin/python`（pytest 与冒烟均成功），`PYTHONPATH=.` 指向项目根以匹配 `backend.src` 导入路径。

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | 本机 `http_proxy` 导致直连 `curl 127.0.0.1:8099` 失败，需 `--noproxy '*'` | 环境 | 自动化脚本显式禁用代理或设置 NO_PROXY |
| 2 | `backend/.venv` 与项目根 `.venv` 并存，易混淆 | 工程 | 统一文档约定单一 venv 路径 |
