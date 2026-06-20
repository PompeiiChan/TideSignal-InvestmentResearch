# T-028 完成报告：Hybrid 调参 + Citation 加固

> **任务 ID**：T-028  
> **完成时间**：2026-06-20

## 变更摘要

### Hybrid 调参（T-027 延续）

- `citation_context_compact.py`：`COMPACT_SNIPPET_MAX_CHARS` **480 → 800**

### Citation 加固

| 文件 | 改动 |
|------|------|
| `citation_rules.py` | 扩展 factual/narrative 检测；`count_paragraphs_missing_citations` |
| `citation_fix.py` | 段落级补标、RAG 长 token 匹配、API 路由、`pick_best_citation_content`、patch prompt 800 字 |
| `response_assembly.py` | missing before/after trace；retry 不回退 draft |

## 测试

- `test_citation_rules.py` +2
- `test_assembly_citation_fix.py` +3（叙述段、pick_best、prompt 上限）
- 回归：`test_citation_context_compact.py`、`test_response_assembly_streaming.py` — **24 passed**
