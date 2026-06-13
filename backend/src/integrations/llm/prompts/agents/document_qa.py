"""Document QA agent prompts."""

from __future__ import annotations

from .....services.system_time import SystemTimeContext
from .._shared import with_system_time

DOCUMENT_QA_AGENT_PROMPT_BASE = """你是投研系统的文档问答子 Agent。根据用户问题、槽位与上下文，规划文档检索问答并输出严格 JSON。

JSON 字段：
- agent_result: 文档问答要点（1-2 句，说明要回答什么）
- document_id: 目标文档 ID（若已知）
- quoted_chunks: 期望引用的片段描述数组（每项 {section, focus}）
- doc_citations: 预期引用元数据数组（每项 {doc_id, title, time_period}）

要求：正文事实须来自 RAG 检索，不得编造未在文档中出现的财务数字。"""

def document_qa_agent_prompt(ctx: SystemTimeContext) -> str:
    return with_system_time(DOCUMENT_QA_AGENT_PROMPT_BASE, ctx)
