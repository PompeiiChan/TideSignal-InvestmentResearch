import type { RichBlockType } from '../types/api'

/** Map seeded / demo session titles to showcase rich component types. */
const SHOWCASE_BY_TITLE: Record<string, RichBlockType> = {
  今天涨幅靠前的半导体股票有哪些: 'ranking_table',
  '15元买入未来预期回报率怎么算': 'calculator',
  帮我看一下今天A股行业板块热力图: 'sector_heatmap',
}

const SHOWCASE_LABELS: Record<RichBlockType, string> = {
  ranking_table: '排行表',
  calculator: '测算器',
  sector_heatmap: '热力图',
}

export function showcaseRichBlockLabel(title: string): string | null {
  const type = SHOWCASE_BY_TITLE[title.trim()]
  return type ? SHOWCASE_LABELS[type] : null
}
