import { useCallback, useEffect, useState } from 'react'
import { demoQuotaService } from '../services/demoQuota'
import type { DemoQuota } from '../types/api'

const EMPTY_QUOTA: DemoQuota = {
  enabled: false,
  limit: 5,
  used: 0,
  remaining: 5,
  reset_date: '',
  visitor_id: '',
}

export function useDemoQuota() {
  const [quota, setQuota] = useState<DemoQuota>(EMPTY_QUOTA)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const next = await demoQuotaService.getQuota()
      setQuota(next)
    } catch {
      setQuota(EMPTY_QUOTA)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { quota, loading, refresh }
}
