import { api } from './api'
import type { ApiResponse, DemoQuota } from '../types/api'
import { getDemoVisitorId } from '../utils/demoVisitor'

const useMock = import.meta.env.VITE_USE_MOCK === 'true'

export const demoQuotaService = {
  async getQuota(): Promise<DemoQuota> {
    if (useMock) {
      return {
        enabled: false,
        limit: 5,
        used: 0,
        remaining: 5,
        reset_date: new Date().toISOString().slice(0, 10),
        visitor_id: getDemoVisitorId(),
      }
    }
    const response = await api.get<ApiResponse<DemoQuota>>('/demo/quota')
    return response.data.data
  },
}
