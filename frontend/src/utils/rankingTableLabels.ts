/** Map ranking_table field keys to Chinese column headers (legacy English payloads). */
const RANKING_FIELD_LABELS: Record<string, string> = {
  rank: '排名',
  stock_name: '名称',
  name: '名称',
  pct_change: '涨跌幅',
  close_price: '收盘价',
  turnover_amount: '成交额',
  leader: '领涨股',
  leader_change: '领涨涨幅',
  ticker: '代码',
  排名: '排名',
  股票名称: '股票',
  板块名称: '板块',
  涨跌幅: '涨跌幅',
  收盘价: '收盘价',
}

export function rankingColumnLabel(column: string): string {
  return RANKING_FIELD_LABELS[column] ?? column
}

export function resolveRankingColumns(columns: string[]): Array<{ key: string; label: string }> {
  return columns.map((column) => ({ key: column, label: rankingColumnLabel(column) }))
}
