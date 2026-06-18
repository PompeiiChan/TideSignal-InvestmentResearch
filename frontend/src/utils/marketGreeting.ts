const GREETINGS = {
  weekend: '假期了，我也在。',
  preMarket: '开盘前，先看点什么？',
  lunch: '午间收盘，正好梳理一下。',
  afterClose: '收盘了，复盘或分析，我都在。',
  night: '夜深了，适合安静研究。',
  trading: '盘中有变，问我就好。',
} as const

const MINUTES = {
  nightEnd: 5 * 60 + 30, // 05:30
  preMarketEnd: 9 * 60 + 30, // 09:30
  morningSessionEnd: 12 * 60, // 12:00
  lunchEnd: 13 * 60, // 13:00
  afternoonSessionEnd: 15 * 60, // 15:00
  afterCloseEnd: 20 * 60, // 20:00
} as const

function getShanghaiClock(date: Date) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai',
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(date)

  const weekday = parts.find((part) => part.type === 'weekday')?.value ?? ''
  const hour = Number(parts.find((part) => part.type === 'hour')?.value ?? 0)
  const minute = Number(parts.find((part) => part.type === 'minute')?.value ?? 0)

  return {
    isWeekend: weekday === 'Sat' || weekday === 'Sun',
    totalMinutes: hour * 60 + minute,
  }
}

export function getMarketGreeting(date: Date = new Date()): string {
  const { isWeekend, totalMinutes } = getShanghaiClock(date)

  if (isWeekend) {
    return GREETINGS.weekend
  }

  if (totalMinutes >= MINUTES.afterCloseEnd || totalMinutes < MINUTES.nightEnd) {
    return GREETINGS.night
  }

  if (totalMinutes < MINUTES.preMarketEnd) {
    return GREETINGS.preMarket
  }

  if (totalMinutes < MINUTES.morningSessionEnd) {
    return GREETINGS.trading
  }

  if (totalMinutes < MINUTES.lunchEnd) {
    return GREETINGS.lunch
  }

  if (totalMinutes < MINUTES.afternoonSessionEnd) {
    return GREETINGS.trading
  }

  return GREETINGS.afterClose
}
