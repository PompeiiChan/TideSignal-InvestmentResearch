import { api } from './api'
import type { ApiResponse, DataSourceStatus } from '../types/api'

const useMock = import.meta.env.VITE_USE_MOCK === 'true'

export const dataSourceService = {
  async getDataSourcesStatus(): Promise<ApiResponse<DataSourceStatus>> {
    if (useMock) {
      const mockApi = await import('../mocks/mockApi')
      return mockApi.getDataSourcesStatus()
    }
    const response = await api.get<ApiResponse<DataSourceStatus>>('/data-sources/status')
    return response.data
  },
}
