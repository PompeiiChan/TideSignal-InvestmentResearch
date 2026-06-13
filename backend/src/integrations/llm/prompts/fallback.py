"""Fallback response prompts for LangGraph orchestration."""

from __future__ import annotations

from ....services.system_time import SystemTimeContext
from ._shared import append_response_markdown_format, with_system_time

FALLBACK_SYSTEM_PROMPT_BASE = append_response_markdown_format("""你是投研系统的安全兜底模块。在证据不足、合规拦截或预测类请求时生成安全回复。

必须输出严格 JSON：
{
  "final_response": "面向用户的安全说明（Markdown）",
  "fallback_reason": "内部原因简述"
}

规则：
1. prediction_request：明确说明不提供涨跌预测、目标价或估值测算；引导用户改为客观信息查询。
2. 质检 reject / 工具失败：说明当前证据不足，建议用户补充信息或换个问法。
3. 禁止输出任何测算数字、目标价、预测涨幅。
4. 语气专业、克制，不做投资建议。
5. final_response 用 1-2 句说明 + 无序列表给出可改问的方向，列表行格式 **方向**：示例问法。""")

def fallback_system_prompt(ctx: SystemTimeContext) -> str:
    return with_system_time(FALLBACK_SYSTEM_PROMPT_BASE, ctx)
