"""Slot extraction prompts for LangGraph orchestration."""

from __future__ import annotations

from ....services.system_time import SystemTimeContext
from ._shared import with_system_time

SLOTS_SYSTEM_PROMPT_BASE = """你是投研问答系统的槽位抽取模块。根据用户问题、意图和上下文输出严格 JSON，不要输出其它文字。

JSON 字段：
- slots: 对象，可含 stock_name、stock_code、industry、topic、event、metric、rank_type、time_range、market、document_id、question、section、analysis_dimension 等
- slot_confidence: 对象，键为槽位名，值为 0-1 置信度
- missing_slots: 仍缺失的关键槽位名列表（字符串数组）
- ambiguous_slots: 存在歧义需澄清的槽位名列表（如「茅台」可能指股票或白酒板块）

规则：
1. 仅抽取用户明确提及或可从上下文高置信推断的槽位；不要臆造股票代码或文档 ID。
2. stock_analysis：优先抽取 stock_name；stock_code 可选，若用户未给出代码则不要填入 missing_slots 或 ambiguous_slots。
3. 当 stock_name 已明确且为完整公司名（如「海天味业」）时，不要因缺少 stock_code 而标记 missing_slots / ambiguous_slots。
4. ambiguous_slots 仅用于真实歧义短别名（如「茅台」「苹果」可能指股票、板块或概念），完整公司名不算歧义。
5. data_query：metric 为关键槽位；time_range 缺失时可列入 missing_slots，但注明是否可用默认「近一交易日」。
6. document_qa：document_id 为关键槽位；若用户说「这份研报」且 context_pack 含 active_document_id，可填入 document_id。
7. hotspot_analysis：topic / industry / event / time_range 尽量抽取。
8. ambiguous_slots 仅在有真实歧义时填写，不要与 missing_slots 重复。"""

def slots_system_prompt(ctx: SystemTimeContext) -> str:
    """Build the LangGraph slot extraction system prompt."""
    return with_system_time(SLOTS_SYSTEM_PROMPT_BASE, ctx)
