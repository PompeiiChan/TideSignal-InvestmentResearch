import { useMemo } from 'react'
import type { SectorHeatmapPayload } from '../types/api'
import { clamp } from '../utils/format'

function formatPct(value: number): string {
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

function formatTurnover(value: number): string {
  const abs = Math.abs(value)
  if (abs >= 1e8) return `${(value / 1e8).toFixed(1)}亿`
  if (abs >= 1e4) return `${(value / 1e4).toFixed(1)}万`
  return value.toFixed(0)
}

function heatColor(pct: number): string {
  const intensity = clamp(Math.abs(pct) / 5, 0.18, 1)
  if (pct > 0.05) {
    return `rgba(220, 38, 38, ${0.12 + intensity * 0.55})`
  }
  if (pct < -0.05) {
    return `rgba(22, 163, 74, ${0.12 + intensity * 0.55})`
  }
  return 'rgba(148, 163, 184, 0.22)'
}

export function SectorHeatmap({ payload }: { payload: SectorHeatmapPayload }) {
  const tiles = useMemo(() => {
    const list = [...payload.tiles]
    const turnovers = list.map((tile) => Math.max(tile.turnover_amount, 1))
    const minTurnover = Math.min(...turnovers)
    const maxTurnover = Math.max(...turnovers)
    return list
      .sort((a, b) => b.turnover_amount - a.turnover_amount)
      .map((tile) => {
        const turnover = Math.max(tile.turnover_amount, 1)
        const weight = turnover / minTurnover
        const span = clamp(Math.round((turnover / maxTurnover) * 3) + 1, 1, 4)
        return { ...tile, weight, span }
      })
  }, [payload.tiles])

  return (
    <div className="sector-heatmap">
      <div className="sector-heatmap-meta">
        <span>{payload.board_kind === 'industry' ? '行业板块' : payload.board_kind}</span>
        {payload.trade_date ? <span>交易日 {payload.trade_date}</span> : null}
        <span>面积按成交额 · 共 {tiles.length} 个板块</span>
      </div>
      <div className="sector-heatmap-grid">
        {tiles.map((tile) => (
          <div
            key={tile.board_code || tile.board_name}
            className="heatmap-tile"
            style={{
              flexGrow: tile.weight,
              flexBasis: `${clamp(tile.span * 14, 18, 42)}%`,
              backgroundColor: heatColor(tile.pct_change),
            }}
            title={`${tile.board_name} ${formatPct(tile.pct_change)} · 成交额 ${formatTurnover(tile.turnover_amount)}`}
          >
            <div className="heatmap-tile-name">{tile.board_name}</div>
            <div className={`heatmap-tile-pct ${tile.pct_change >= 0 ? 'up' : 'down'}`}>{formatPct(tile.pct_change)}</div>
            <div className="heatmap-tile-sub">
              {tile.leader ? `${tile.leader}` : '—'}
              {tile.leader_change != null ? ` ${formatPct(Number(tile.leader_change))}` : ''}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
