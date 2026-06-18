import { useMemo, useState } from 'react'
import type { ScenarioCalculatorPayload } from '../types/api'
import { formatYuan } from '../utils/format'
import { computeBuyPriceFromReturn, computeGrossProfit, computeReturnRate, roundPrice, roundReturnRate } from '../utils/returnCalc'

function CitationTag({ index }: { index?: number | null }) {
  if (!index) return null
  return <span className="citation-tag">[{index}]</span>
}

function SourceLine({ source }: { source: ScenarioCalculatorPayload['buy_price_source'] }) {
  if (!source?.title) return null
  return (
    <div className="scenario-source scenario-source--compact">
      <span className="scenario-source-label">假设来源</span>
      <div className="scenario-source-line">
        <span>{source.title}</span>
        <CitationTag index={source.citation_index} />
      </div>
    </div>
  )
}

export function ScenarioCalculator({ payload }: { payload: ScenarioCalculatorPayload }) {
  const defaultKey = payload.active_scenario || payload.scenarios[0]?.key || 'base'
  const [activeKey, setActiveKey] = useState(defaultKey)
  const [buyPrice, setBuyPrice] = useState(roundPrice(Number(payload.buy_price)))
  const [shareCount, setShareCount] = useState(Number(payload.share_count || 100))

  const activeScenario = payload.scenarios.find((item) => item.key === activeKey) ?? payload.scenarios[0]
  const targetPrice = Number(activeScenario?.target_price ?? payload.buy_price)

  const [returnRatePct, setReturnRatePct] = useState(() =>
    roundReturnRate(computeReturnRate(Number(payload.buy_price), targetPrice)),
  )

  const results = useMemo(() => {
    const cost = buyPrice * shareCount
    const profit = computeGrossProfit(buyPrice, targetPrice, shareCount)
    return {
      profitAmount: formatYuan(profit),
      costAmount: formatYuan(cost),
    }
  }, [buyPrice, shareCount, targetPrice])

  const handleScenarioChange = (key: string) => {
    setActiveKey(key)
    const scenario = payload.scenarios.find((item) => item.key === key)
    const nextTarget = Number(scenario?.target_price ?? payload.buy_price)
    setReturnRatePct(roundReturnRate(computeReturnRate(buyPrice, nextTarget)))
  }

  const handleBuyPriceChange = (value: number) => {
    const rounded = roundPrice(value)
    setBuyPrice(rounded)
    setReturnRatePct(roundReturnRate(computeReturnRate(rounded, targetPrice)))
  }

  const handleReturnRateChange = (value: number) => {
    const rounded = roundReturnRate(value)
    setReturnRatePct(rounded)
    setBuyPrice(computeBuyPriceFromReturn(targetPrice, rounded))
  }

  return (
    <div className="scenario-calculator">
      {payload.stock_name ? <p className="scenario-stock">{payload.stock_name}</p> : null}
      {payload.reference_year ? (
        <p className="scenario-meta">
          基准年 {payload.reference_year}；情景预测 2026E / 2027E / 2028E
          {payload.low_coverage ? '（机构覆盖偏少，仅供参考）' : ''}
        </p>
      ) : null}
      {payload.formula ? <p className="scenario-formula">公式：{payload.formula}</p> : null}
      <div className="scenario-tabs">
        {payload.scenarios.map((scenario) => {
          const previewRate =
            scenario.return_pct !== undefined && scenario.return_pct !== null
              ? `${Number(scenario.return_pct).toFixed(1)}%`
              : '—'
          return (
            <button
              key={scenario.key}
              type="button"
              className={`scenario-tab${scenario.key === activeKey ? ' active' : ''}`}
              onClick={() => handleScenarioChange(scenario.key)}
            >
              <span>{scenario.label}</span>
              <strong>{previewRate}</strong>
            </button>
          )
        })}
      </div>
      {activeScenario ? (
        <>
          <p className="scenario-assumption">{activeScenario.assumption}</p>
          {activeScenario.eps !== undefined && activeScenario.pe !== undefined ? (
            <p className="scenario-eps-pe">
              {activeScenario.forecast_year ? `${activeScenario.forecast_year}E：` : ''}
              EPS {activeScenario.eps} × PE {activeScenario.pe} = 情景价 {targetPrice.toFixed(2)} 元
            </p>
          ) : null}
          <SourceLine source={activeScenario.source} />
        </>
      ) : null}
      <div className="scenario-buy-source">
        <span>
          买入价来源：{payload.buy_price_source?.title || '实时行情'}
          <CitationTag index={payload.buy_price_source?.citation_index} />
        </span>
      </div>
      <p className="scenario-disclaimer">本测算不包含交易成本和时间成本。</p>
      <label className="calc-field">
        <span>买入价</span>
        <input
          type="number"
          value={buyPrice}
          step="0.01"
          onChange={(event) => handleBuyPriceChange(Number(event.target.value || 0))}
        />
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
        <input type="number" value={targetPrice} step="0.01" readOnly className="readonly" />
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
      <p className="scenario-calc-tip">可调整买入价测算收益率，也可输入目标收益率反推买入价。</p>
    </div>
  )
}
