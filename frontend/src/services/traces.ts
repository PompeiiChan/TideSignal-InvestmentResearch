import { api } from './api'
import type { ApiResponse, RawTraceStepResponse, Trace } from '../types/api'

const useMock = import.meta.env.VITE_USE_MOCK === 'true'

export const traceService = {
  async getTrace(traceId: string): Promise<ApiResponse<Trace>> {
    if (useMock) {
      const mockApi = await import('../mocks/mockApi')
      return mockApi.getTrace(traceId)
    }
    const response = await api.get<ApiResponse<Trace>>(`/traces/${traceId}`)
    return response.data
  },
  async getTraceStepRaw(traceId: string, stepId: string): Promise<ApiResponse<RawTraceStepResponse>> {
    if (useMock) {
      const mockApi = await import('../mocks/mockApi')
      return mockApi.getTraceStepRaw(traceId, stepId)
    }
    const response = await api.get<ApiResponse<RawTraceStepResponse>>(`/traces/${traceId}/steps/${stepId}/raw`)
    return response.data
  },
}
