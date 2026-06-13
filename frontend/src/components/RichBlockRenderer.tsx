import { useMemo, useState } from 'react'
import type { CalculatorPayload, RankingTablePayload, RichBlock, SectorHeatmapPayload } from '../types/api'
import { formatYuan } from '../utils/format'
import { normalizeCalculatorPayload } from '../utils/richBlockPayload'
import { SectorHeatmap } from './SectorHeatmap'

function isRankingPayload(payload: RichBlock['payload']): payload is RankingTablePayload {
  return 'columns' in payload && 'rows' in payload
}

function isCalculatorPayload(payload: RichBlock['payload']): payload is CalculatorPayload {
  return normalizeCalculatorPayload(payload) !== null
}

function isHeatmapPayload(payload: RichBlock['payload']): payload is SectorHeatmapPayload {
  return 'tiles' in payload && Array.isArray((payload as SectorHeatmapPayload).tiles)
}

function DataTable({ payload }: { payload: RankingTablePayload }) {
  return (
    <table className="data-table">
      <thead>
        <tr>
          {payload.columns.map((column) => (
            <th key={column}>{column}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {payload.rows.map((row, index) => (
          <tr key={index}>
            {payload.columns.map((column) => {
              const value = row[column]
              return (
                <td key={`${index}-${column}`} className={String(value ?? '').startsWith('+') ? 'up' : undefined}>
                  {value ?? '—'}
                </td>
              )
            })}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Calculator({ payload }: { payload: CalculatorPayload }) {
  const defaults = Object.fromEntries(payload.fields.map((field) => [field.key, field.value]))
  const [buyPrice, setBuyPrice] = useState(Number(defaults.buy_price ?? 15))
  const [targetPrice, setTargetPrice] = useState(Number(defaults.target_price ?? 20))
  const [shareCount, setShareCount] = useState(Number(defaults.share_count ?? 1000))
  const [feeRate, setFeeRate] = useState(Number(defaults.fee_rate ?? 0.03))

  const results = useMemo(() => {
    const cost = buyPrice * shareCount
    const gross = (targetPrice - buyPrice) * shareCount
    const fees = (buyPrice + targetPrice) * shareCount * (feeRate / 100)
    const profit = gross - fees
    const rate = cost ? (profit / cost) * 100 : 0
    return {
      returnRate: `${rate.toFixed(2)}%`,
      profitAmount: formatYuan(profit),
      costAmount: formatYuan(cost),
    }
  }, [buyPrice, feeRate, shareCount, targetPrice])

  return (
    <div className="calculator">
      <label className="calc-field">
        <span>买入价</span>
        <input type="number" value={buyPrice} step="0.01" onChange={(event) => setBuyPrice(Number(event.target.value || 0))} />
      </label>
      <label className="calc-field">
        <span>情景价</span>
        <input type="number" value={targetPrice} step="0.01" onChange={(event) => setTargetPrice(Number(event.target.value || 0))} />
      </label>
      <label className="calc-field">
        <span>持仓数量</span>
        <input type="number" value={shareCount} step="100" onChange={(event) => setShareCount(Number(event.target.value || 0))} />
      </label>
      <label className="calc-field">
        <span>估算费率</span>
        <input type="number" value={feeRate} step="0.01" onChange={(event) => setFeeRate(Number(event.target.value || 0))} />
      </label>
      <div className="calc-result">
        <div className="result-tile">
          <span>收益率</span>
          <strong>{results.returnRate}</strong>
        </div>
        <div className="result-tile">
          <span>预估盈亏</span>
          <strong>{results.profitAmount}</strong>
        </div>
        <div className="result-tile">
          <span>测算成本</span>
          <strong>{results.costAmount}</strong>
        </div>
      </div>
    </div>
  )
}

export function RichBlockRenderer({ block }: { block: RichBlock }) {
  if (block.type === 'ranking_table' && isRankingPayload(block.payload)) {
    return (
      <div className="rich-card">
        <div className="rich-head">
          <span>{block.title}</span>
          <span className="pill primary">结构化数据</span>
        </div>
        <div className="rich-body">
          <DataTable payload={block.payload} />
        </div>
      </div>
    )
  }

  if (block.type === 'calculator' && isCalculatorPayload(block.payload)) {
    const normalized = normalizeCalculatorPayload(block.payload)
    if (!normalized) return null
    return (
      <div className="rich-card">
        <div className="rich-head">
          <span>{block.title}</span>
          <span className="pill primary">可交互</span>
        </div>
        <Calculator payload={normalized} />
      </div>
    )
  }

  if (block.type === 'sector_heatmap' && isHeatmapPayload(block.payload)) {
    return (
      <div className="rich-card">
        <div className="rich-head">
          <span>{block.title}</span>
          <span className="pill primary">热力图</span>
        </div>
        <div className="rich-body sector-heatmap-body">
          <SectorHeatmap payload={block.payload} />
        </div>
      </div>
    )
  }

  return null
}
