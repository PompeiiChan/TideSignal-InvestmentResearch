import type { SourceRef } from '../types/api'

export const MODEL_OWN_KNOWLEDGE_LABEL = '模型自有知识，可能存在错误'

export function isModelOwnKnowledgeSource(source: SourceRef): boolean {
  if (source.label === MODEL_OWN_KNOWLEDGE_LABEL) return true
  return source.label === '模型整理' && (source.time === '本轮会话' || !source.time)
}

export function normalizeSourceRef(source: SourceRef): SourceRef {
  if (!isModelOwnKnowledgeSource(source)) return source
  return { type: 'knowledge', label: MODEL_OWN_KNOWLEDGE_LABEL }
}
