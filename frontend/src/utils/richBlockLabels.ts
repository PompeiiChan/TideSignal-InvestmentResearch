import type { RichBlock, RichBlockType } from '../types/api'

export const RICH_BLOCK_LABELS: Record<RichBlockType, string> = {
  ranking_table: '排行表',
  calculator: '测算器',
  sector_heatmap: '热力图',
  scenario_calculator: '情景测算',
}

const RICH_BLOCK_ORDER: RichBlockType[] = [
  'ranking_table',
  'sector_heatmap',
  'calculator',
  'scenario_calculator',
]

const ALLOWED_TYPES = new Set<RichBlockType>(RICH_BLOCK_ORDER)

export function richBlockTypeLabels(types: Array<RichBlockType | string> | undefined): string[] {
  return (types ?? [])
    .map((type) => RICH_BLOCK_LABELS[type as RichBlockType])
    .filter((label): label is string => Boolean(label))
}

export function extractRichBlockTypes(blocks: RichBlock[]): RichBlockType[] {
  const seen = new Set<RichBlockType>()
  const ordered: RichBlockType[] = []
  for (const type of RICH_BLOCK_ORDER) {
    if (blocks.some((block) => block.type === type) && !seen.has(type)) {
      ordered.push(type)
      seen.add(type)
    }
  }
  for (const block of blocks) {
    if (ALLOWED_TYPES.has(block.type) && !seen.has(block.type)) {
      ordered.push(block.type)
      seen.add(block.type)
    }
  }
  return ordered
}
