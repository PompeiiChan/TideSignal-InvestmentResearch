# T-010 Developer Report — Embedding + 本地 Markdown 知识库检索

## 第 2 次返工（Tester FAIL 修复）

### 根因与修复

| FAIL 项 | 修复 |
|---------|------|
| 2081 chunks 全量索引 60s 超时失败 | `EMBEDDING_TIMEOUT` 可配置（默认 180s）；`embed_texts` 3 次指数退避重试；batch size 8→4 |
| 8 分钟白跑无 `.index/` | 索引改为 `chunks.jsonl`/`vectors.jsonl` 分批 append；支持 `build_in_progress` 断点续建 |
| `EmbeddingClientError` 导致 Chat 500 | `ensure_index`/`retrieve` 捕获并包装为 `RagNotReadyError` 或 `mode=mock` 降级 |
| chunk 过多 | `_MAX_CHUNK_CHARS` 1200→2400，最小 chunk 40→80，chunk 数 2081→**1036** |

### 变更文件（返工）

- `backend/src/settings.py` — `embedding_timeout` / `EMBEDDING_TIMEOUT`
- `backend/.env.example` — `EMBEDDING_TIMEOUT=180`
- `backend/src/integrations/embedding/service.py` — 超时读取 settings + 重试
- `backend/src/services/rag/index_store.py` — JSONL 断点索引
- `backend/src/services/rag/service.py` — 续建、错误降级、batch=4
- `backend/src/services/rag/chunker.py` — 更大 chunk 减少调用次数
- `backend/tests/test_rag_service.py` — 断点/降级单测；`live_rag_service` 复用已建索引

## 真实索引构建结果（Developer 验证）

| 指标 | 值 |
|------|-----|
| Markdown 文件数 | 36 |
| 索引 chunk 数 | **1036**（优化前 2081） |
| 构建耗时 | **621.9s（~10.4 分钟）** |
| 索引路径 | `backend/data/knowledge-base/.index/` |
| 中途上游 500 | 第 1 批重试后成功继续 |

## 四类 RAG smoke（真实索引）

| 类别 | 提问 | 结果 | Top 命中 |
|------|------|------|----------|
| 热点 market | 2026年6月A股市场热点有哪些 | PASS | 2026 年 6 月 A股月度热点文档 |
| 财报 financial | 宁德时代2025年报营收和利润表现如何 | PASS | 宁德时代（300750）财务资料 |
| 行业研报 report | 白酒行业2026年行业研报怎么看 | PASS | 白酒行业研报：2026年度投资策略 |
| 公司研报 report | 海天味业2026年公司研报核心观点 | PASS | 海天味业公司研报 |

## 测试命令与结果

```bash
.venv/bin/python -m ruff check backend/src backend/tests   # PASS
.venv/bin/python -m mypy backend/src backend/tests         # PASS
.venv/bin/python -m pytest backend/tests                     # 28 passed, 6 skipped
REAL_API_TEST=1 .venv/bin/python -m pytest backend/tests/test_rag_service.py -q  # 12 passed (~11s，复用已建索引)
cd frontend && npm run type-check && npm run lint && npm run build  # PASS
```

## 前端联调说明

1. `VITE_USE_MOCK=false`，后端 8099 / 前端 5199
2. 首次提问会触发索引构建（约 10 分钟，已建索引则秒级检索）
3. `GET /api/data-sources/status`：`rag.mode=semantic`、`rag.status=ready`（索引完成后）
4. Chat 索引失败时降级为 mock 检索，**不再 HTTP 500**

**本功能返工已完成，等待 Orchestrator 调度 Tester 复验。**
