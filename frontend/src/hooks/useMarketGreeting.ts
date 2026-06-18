import { useEffect, useState } from 'react'
import { getMarketGreeting } from '../utils/marketGreeting'

export function useMarketGreeting() {
  const [greeting, setGreeting] = useState(() => getMarketGreeting())

  useEffect(() => {
    const sync = () => setGreeting(getMarketGreeting())
    sync()
    const timer = window.setInterval(sync, 60_000)
    return () => window.clearInterval(timer)
  }, [])

  return greeting
}
