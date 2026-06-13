import { api } from './api'
import type { ApiResponse, ConfigStatus } from '../types/api'

const useMock = import.meta.env.VITE_USE_MOCK === 'true'

export const configService = {
  async getConfigStatus(): Promise<ApiResponse<ConfigStatus>> {
    if (useMock) {
      const mockApi = await import('../mocks/mockApi')
      return mockApi.getConfigStatus()
    }
    const response = await api.get<ApiResponse<ConfigStatus>>('/config/status')
    return response.data
  },
}
