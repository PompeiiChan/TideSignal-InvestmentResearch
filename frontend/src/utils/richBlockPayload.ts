import type { CalculatorPayload, RichBlockPayload } from '../types/api'

type FlatCalculatorPayload = {
  buy_price?: number
  sell_price?: number
  target_price?: number
  share_count?: number
  fee_rate?: number
  net_profit?: number
  return_pct?: number
  formula?: string
}

function isFlatCalculatorPayload(payload: RichBlockPayload): payload is FlatCalculatorPayload {
  return 'buy_price' in payload || 'sell_price' in payload || 'target_price' in payload
}

export function normalizeCalculatorPayload(payload: RichBlockPayload): CalculatorPayload | null {
  if ('fields' in payload && 'results' in payload) {
    return payload as CalculatorPayload
  }
  if (!isFlatCalculatorPayload(payload)) {
    return null
  }
  const buyPrice = Number(payload.buy_price ?? 0)
  const targetPrice = Number(payload.sell_price ?? payload.target_price ?? 0)
  const shareCount = Number(payload.share_count ?? 100)
  const cost = buyPrice * shareCount
  return {
    fields: [
      { key: 'buy_price', label: '买入价', value: buyPrice, unit: '元' },
      { key: 'target_price', label: '情景价', value: targetPrice, unit: '元' },
      { key: 'share_count', label: '持仓数量', value: shareCount, unit: '股' },
    ],
    results: [
      {
        key: 'return_rate',
        label: '收益率',
        value: payload.return_pct != null ? `${Number(payload.return_pct).toFixed(2)}%` : '—',
      },
      {
        key: 'profit_amount',
        label: '预估盈亏',
        value: payload.net_profit != null ? `${Number(payload.net_profit).toFixed(2)} 元` : '—',
      },
      {
        key: 'cost_amount',
        label: '测算成本',
        value: `${cost.toFixed(2)} 元`,
      },
    ],
  }
}
