/** Gross return formulas used by interactive calculators (excludes fees and time cost). */

export function computeReturnRate(buyPrice: number, targetPrice: number): number {
  if (!buyPrice || buyPrice <= 0) return 0
  return ((targetPrice - buyPrice) / buyPrice) * 100
}

export function computeBuyPriceFromReturn(targetPrice: number, returnRatePct: number): number {
  const divisor = 1 + returnRatePct / 100
  if (!divisor || divisor <= 0) return 0
  return roundPrice(targetPrice / divisor)
}

export function computeGrossProfit(buyPrice: number, targetPrice: number, shareCount: number): number {
  return (targetPrice - buyPrice) * shareCount
}

export function roundPrice(value: number): number {
  return Math.round(value * 100) / 100
}

export function roundReturnRate(value: number): number {
  return Math.round(value * 100) / 100
}
