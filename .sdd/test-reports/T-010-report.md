# 测试报告：T-010 Embedding + 本地 Markdown 知识库检索

**测试时间**：2026-06-12（第 2 轮复验）
**Tester Agent ID**：cursor-tester

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 客户端询问热点/财报/行业研报/公司研报，回答展示本地知识库真实引用（标题、来源类型）且内容相关 | **PASS** | `POST /api/chat/query`（热点问题）HTTP **200**（~26s）；`citation_list` 含 `2026 年 6 月 A股月度热点文档` 等，`type=market`；`REAL_API_TEST=1` 四类 parametrized 用例 12/12 通过 |
| 2 | 管理端 Trace RAG 节点可见命中文档标题、分数或相关性说明 | **PASS** | `GET /api/traces/trace_20260612_024159_002_local` → `rag_retrieval` 节点 `status=success`，`rag_hits` 含标题、`source_type`、`score`（如 0.8152） |
| 3 | 数据说明页：知识库目录、真实 md 数、ready 状态；热点与样本公司行情分别展示 | **PASS** | `GET /api/data-sources/status`：`knowledge.path=data/knowledge-base`、`sample_count=36`、`status=ready`；`rag.mode=semantic`、`rag.status=ready`；行情等 mock 数据源独立展示 |
| 4 | 系统设置页：Embedding 字段名和 ready 状态，无真实密钥 | **PASS** | `GET /api/config/status`：Embedding 四字段名可见、`status=ready`；响应体无 `sk-` 密钥 |

## technicalChecks 逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | ruff check backend/src backend/tests | **PASS** | `All checks passed!` |
| 2 | mypy backend/src backend/tests | **PASS** | `Success: no issues found in 51 source files` |
| 3 | pytest backend/tests | **PASS** | `28 passed, 6 skipped` |
| 4 | frontend type-check / lint / build | **PASS** | 三项均 exit 0 |
| 5 | EMBEDDING_* / LOCAL_KB_PATH 从 .env 读取 | **PASS** | 配置经 `AppSettings`；`.sdd/**` 无密钥泄露 |
| 6 | 知识库 36 md；`.index/` 可 gitignore | **PASS** | `count_markdown_files==36`；`.index/` 含 `index_meta.json`、`chunks.jsonl`、`vectors.jsonl` |
| 7 | Embedding httpx trust_env=False | **PASS** | `embedding/client.py:57` |
| 8 | VITE_USE_MOCK=false；/api 代理 8099 | **PASS** | `frontend/.env`：`VITE_USE_MOCK=false`、`VITE_API_BASE_URL=/api` |
| 9 | 四类文档各 ≥1 RAG 命中 | **PASS** | `REAL_API_TEST=1 pytest backend/tests/test_rag_service.py` → **12 passed in 10.85s**（market/financial/report×2） |
| 10 | 真实 Embedding + 本地检索 | **PASS** | `RagService.has_index()==True`、`is_ready()==True`；`index_meta.json`：`chunk_count=1036`、`build_in_progress=false`、`embedding_dim=4096` |
| 11 | 外部服务失败清晰处理，Chat 不 500 | **PASS** | 索引已存在时 Chat 200；返工代码在 `rag/service.py` 捕获 `EmbeddingClientError` 降级（单测覆盖） |

## 与第 1 轮 FAIL 对比

| 上轮问题 | 本轮验证 |
|---------|---------|
| 全量索引超时、无 `.index/` | **已修复**：`.index/` 存在，1036 chunks，`build_in_progress=false` |
| Chat 500 | **已修复**：热点问答 HTTP 200 |
| RAG status mocked | **已修复**：`rag.mode=semantic`、`rag.status=ready` |

## 验证证据摘要

```text
has_index: True | is_ready: True | md_count: 36
index_meta: chunk_count=1036, embedding_model=Qwen/Qwen3-Embedding-8B, embedding_dim=4096

REAL_API_TEST=1 pytest test_rag_service.py → 12 passed in 10.85s

GET /api/data-sources/status → rag.mode=semantic, rag.status=ready, knowledge.sample_count=36
GET /api/config/status → Embedding status=ready, no sk- in response

POST /api/chat/query (热点) → HTTP 200, citations with market type
GET /api/traces/... → rag_retrieval rag_hits with title + score
```

## 第 1 轮 FAIL 问题修复确认

| # | 问题 | 状态 |
|---|------|------|
| 1 | 全量索引 60s 超时、无 `.index/` | **已修复** |
| 2 | Chat 500 | **已修复** |
| 3 | RAG status mocked | **已修复** |
