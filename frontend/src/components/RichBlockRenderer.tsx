import { useMemo, useState } from 'react'
import type { CalculatorPayload, RankingTablePayload, RichBlock, ScenarioCalculatorPayload, SectorHeatmapPayload } from '../types/api'
import { resolveRankingColumns } from '../utils/rankingTableLabels'
import { normalizeCalculatorPayload } from '../utils/richBlockPayload'
import { computeBuyPriceFromReturn, computeGrossProfit, computeReturnRate, roundPrice, roundReturnRate } from '../utils/returnCalc'
import { ScenarioCalculator } from './ScenarioCalculator'
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

function isScenarioCalculatorPayload(payload: RichBlock['payload']): payload is ScenarioCalculatorPayload {
  return 'scenarios' in payload && Array.isArray((payload as ScenarioCalculatorPayload).scenarios)
}

function DataTable({ payload }: { payload: RankingTablePayload }) {
  const columnDefs = resolveRankingColumns(payload.columns)

  return (
    <table className="data-table">
      <thead>
        <tr>
          {columnDefs.map((column) => (
            <th key={column.key}>{column.label}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {payload.rows.map((row, index) => (
          <tr key={index}>
            {columnDefs.map((column) => {
              const value = row[column.key]
              const display = value == null || value === '' ? '—' : String(value)
              return (
                <td key={`${index}-${column.key}`} className={display.startsWith('+') ? 'up' : undefined}>
                  {display}
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
  const initialBuyPrice = Number(defaults.buy_price ?? 15)
  const initialTargetPrice = Number(defaults.target_price ?? 20)
  const [buyPrice, setBuyPrice] = useState(roundPrice(initialBuyPrice))
  const [targetPrice, setTargetPrice] = useState(initialTargetPrice)
  const [shareCount, setShareCount] = useState(Number(defaults.share_count ?? 100))
  const [returnRatePct, setReturnRatePct] = useState(() =>
    roundReturnRate(computeReturnRate(initialBuyPrice, initialTargetPrice)),
  )

  const results = useMemo(() => {
    const cost = buyPrice * shareCount
    const profit = computeGrossProfit(buyPrice, targetPrice, shareCount)
    return {
      profitAmount: formatYuan(profit),
      costAmount: formatYuan(cost),
    }
  }, [buyPrice, shareCount, targetPrice])

  const handleBuyPriceChange = (value: number) => {
    const rounded = roundPrice(value)
    setBuyPrice(rounded)
    setReturnRatePct(roundReturnRate(computeReturnRate(rounded, targetPrice)))
  }

  const handleTargetPriceChange = (value: number) => {
    setTargetPrice(value)
    setReturnRatePct(roundReturnRate(computeReturnRate(buyPrice, value)))
  }

  const handleReturnRateChange = (value: number) => {
    const rounded = roundReturnRate(value)
    setReturnRatePct(rounded)
    setBuyPrice(computeBuyPriceFromReturn(targetPrice, rounded))
  }

  return (
    <div className="calculator">
      {payload.assumption ? <p className="calc-assumption">{payload.assumption}</p> : null}
      <p className="scenario-disclaimer">本测算不包含交易成本和时间成本。</p>
      <label className="calc-field">
        <span>买入价</span>
        <input type="number" value={buyPrice} step="0.01" onChange={(event) => handleBuyPriceChange(Number(event.target.value || 0))} />
      </label>
      <label className="calc-field">
        <span>预期收益率（%）</span>
        <input
          type="number"
          value={returnRatePct}
          step="0.01"
          onChange={(event) => handleReturnRateChange(Number(event.target.value || 0))}
        />
      </label>
      <label className="calc-field">
        <span>情景价</span>
        <input type="number" value={targetPrice} step="0.01" onChange={(event) => handleTargetPriceChange(Number(event.target.value || 0))} />
      </label>
      <label className="calc-field">
        <span>持仓数量</span>
        <input type="number" value={shareCount} step="100" onChange={(event) => setShareCount(Number(event.target.value || 0))} />
      </label>
      <div className="calc-result calc-result--two">
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

  if (block.type === 'scenario_calculator' && isScenarioCalculatorPayload(block.payload)) {
    return (
      <div className="rich-card">
        <div className="rich-head">
          <span>{block.title}</span>
          <span className="pill primary">情景测算</span>
        </div>
        <ScenarioCalculator payload={block.payload} />
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
