# T-028 Hybrid 调参 + Citation 加固 — 技术方案

> **任务 ID**：T-028  
> **依赖**：T-027  
> **背景**：T-027 compact 后首字变快，但深度问股 citation 漏标仍多；用户要求 hybrid 调参 + citation 加固并行，不回滚 compact。

## 目标

1. **Hybrid**：compact RAG snippet 480 → **800**，保留 JSON 瘦身与其它 compact 策略。
2. **Citation 加固**：扩大漏标检测、改进程序补标、LLM patch 失败时不回退未补标首稿。

## 实现

### Hybrid（T-027 调参）

- `COMPACT_SNIPPET_MAX_CHARS = 800`

### Citation 规则（`citation_rules.py`）

- 扩展 `FACTUAL_PARAGRAPH_RE`（研报/行业/预期等关键词）
- 长叙述段（≥48 字 + 公司/行业/业务等）也要求段末 citation
- 新增 `count_paragraphs_missing_citations()`

### Citation 补标（`citation_fix.py`）

- 段落级精确匹配补标（非 80 字前缀）
- RAG catalog 标题更长 token 匹配；API 公告关键词路由
- `pick_best_citation_content()`：多候选取漏标最少版本
- patch prompt 上限 500 → **800**，最多 hint **4** 段

### Assembly（`response_assembly.py`）

- Trace：`citation_missing_before_patch` / `citation_missing_after_patch`
- LLM citation retry 基于 **已程序补标** 的 `content`
- retry 失败 → `pick_best_citation_content(revised, patched, draft)`，不回退裸 draft

## 验收

| AC | 标准 |
|----|------|
| 1 | compact snippet 常量为 800 |
| 2 | 叙述性 RAG 段落纳入 citation 检测 |
| 3 | patch 失败时保留程序补标结果 |
| 4 | Trace 可见 citation_missing_before/after |
| 5 | 单测 + assembly streaming 回归通过 |
