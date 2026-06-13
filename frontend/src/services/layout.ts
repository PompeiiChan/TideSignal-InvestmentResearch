import { api } from './api'
import type { ApiResponse, LayoutPreferences } from '../types/api'

const useMock = import.meta.env.VITE_USE_MOCK === 'true'

export const layoutService = {
  async getLayoutPreferences(): Promise<ApiResponse<LayoutPreferences>> {
    if (useMock) {
      const mockApi = await import('../mocks/mockApi')
      return mockApi.getLayoutPreferences()
    }
    const response = await api.get<ApiResponse<LayoutPreferences>>('/layout/preferences')
    return response.data
  },
  async patchLayoutPreferences(sidebarWidth: number, tracePanelWidth: number): Promise<ApiResponse<LayoutPreferences>> {
    if (useMock) {
      const mockApi = await import('../mocks/mockApi')
      return mockApi.patchLayoutPreferences(sidebarWidth, tracePanelWidth)
    }
    const response = await api.patch<ApiResponse<LayoutPreferences>>('/layout/preferences', {
      sidebar_width: sidebarWidth,
      trace_panel_width: tracePanelWidth,
    })
    return response.data
  },
}
