# 用户验收结果：T-018 问股 live 基本面 Tool（F21）

**验收日期**：2026-06-15  
**验收人**：用户（确认「验收通过」）  
**结论**：**PASS**

## 验收范围

依据 `.sdd/test-reports/acceptance-roadmap-T-018.md`：

- 数据说明页 live 数据源可观测（新浪/同花顺/东财），无密钥泄露
- 未收录 A 股基本面可走新浪 live 财务指标 + 报告期
- 「机构怎么看」展示一致预期或东财研报元数据
- Trace `tool_call` 可见工具归因（`data_origin` / `fallback` / Apache-2.0）
- fallback 不伪装 live PASS；问股边界不接 K 线/盘口

## 代码基线

- 主检查点：本 commit（feat T-018）
- Tester 自动化：`.sdd/test-reports/test-T-018.md`（PASS）

## 后续

- **T-019** 知识库扩容（创业板 50 家财报）进行中，与 T-018 live Tool 并行不冲突
- 可选：东财启动探针、iwencai / PDF 入库（非 T-018 范围）
