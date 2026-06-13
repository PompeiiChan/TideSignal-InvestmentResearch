import type { Message, RichBlock, Session } from '../types/api'

const ALLOWED_RICH_BLOCK_TYPES = new Set(['ranking_table', 'calculator', 'sector_heatmap'])
const DEPRECATED_RICH_BLOCK_TYPES = new Set([
  'text',
  'stock_card',
  'metric_table',
  'trace_summary',
  'citation_list',
  'risk_notice',
  'hotspot',
])

const INTERNAL_TITLES = new Set(['Agent fallback 回答摘要', 'fallback 回答摘要'])
const INTERNAL_PHRASES = [
  '当前回答由演示级 Agent fallback 链路生成',
  'Agent fallback',
  'fallback 链路',
  'fallback 规则',
  '真实 LLM',
  'LangGraph',
  '用于验证路由',
]

const LEGACY_STOCK_BOILERPLATE = '已根据本地模拟数据生成个股基本面信息卡，并附上引用来源和风险提示'

const CONTENT_REPLACEMENTS: Record<string, string> = {
  '已路由到热点助手，基于本地模拟研报与公告生成热点归因摘要。': '下面整理热点归因摘要。',
  '已路由到问数助手，基于本地模拟行情生成结构化排行回答。': '下面是相关行情数据整理。',
}

function containsInternalText(value: unknown): boolean {
  const text = typeof value === 'string' ? value : JSON.stringify(value)
  return INTERNAL_PHRASES.some((phrase) => text.includes(phrase))
}

function stripInternalLines(content: string): string {
  return content
    .split(/\n+/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('问题：') && !containsInternalText(line))
    .join('\n')
    .trim()
}

export function sanitizeAssistantContent(role: string, content: string): string {
  if (role !== 'assistant') return content
  return sanitizeVisibleText(content)
}

export function sanitizeVisibleText(content: string): string {
  const normalized = content.trim()
  if (!normalized) return content

  if (normalized.includes(LEGACY_STOCK_BOILERPLATE)) {
    return stripInternalLines(normalized.replaceAll(LEGACY_STOCK_BOILERPLATE, '').replaceAll('。', ''))
  }

  if (CONTENT_REPLACEMENTS[normalized]) return CONTENT_REPLACEMENTS[normalized]
  if (!containsInternalText(normalized)) return content

  const cleaned = stripInternalLines(normalized)
  return cleaned || content
}

export function sanitizeSession(session: Session): Session {
  return {
    ...session,
    last_message_preview: sanitizeAssistantContent('assistant', session.last_message_preview),
  }
}

export function sanitizeMessage(message: Message): Message {
  if (message.role !== 'assistant') return message
  return {
    ...message,
    content: sanitizeAssistantContent(message.role, message.content),
    rich_blocks: sanitizeRichBlocks(message.role, message.rich_blocks),
  }
}

export function sanitizeMessages(messages: Message[]): Message[] {
  return messages.map(sanitizeMessage)
}

export function sanitizeRichBlocks(role: string, blocks: RichBlock[]): RichBlock[] {
  if (role !== 'assistant') return blocks

  return blocks
    .filter((block) => !isInternalSummaryBlock(block))
    .filter((block) => !DEPRECATED_RICH_BLOCK_TYPES.has(block.type))
    .filter((block) => ALLOWED_RICH_BLOCK_TYPES.has(block.type))
    .map(sanitizeBlock)
    .filter((block) => Boolean(block.payload))
}

function isInternalSummaryBlock(block: RichBlock): boolean {
  if (INTERNAL_TITLES.has(block.title)) return true
  return containsInternalText(block.payload)
}

function sanitizeBlock(block: RichBlock): RichBlock {
  const nextBlock = structuredClone(block)
  if (nextBlock.risk_notice && containsInternalText(nextBlock.risk_notice)) {
    nextBlock.risk_notice = '以上内容仅为信息整理，不构成投资建议。'
  }
  return nextBlock
}
