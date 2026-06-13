import { api } from './api'
import type {
  ApiResponse,
  DeleteSessionResponse,
  PageResult,
  Session,
  SessionDetail,
  SessionSource,
} from '../types/api'

const useMock = import.meta.env.VITE_USE_MOCK === 'true'

export const sessionService = {
  async getSessions(keyword = ''): Promise<ApiResponse<PageResult<Session>>> {
    if (useMock) {
      const mockApi = await import('../mocks/mockApi')
      return mockApi.getSessions(keyword)
    }
    const response = await api.get<ApiResponse<PageResult<Session>>>('/sessions', {
      params: { keyword, page: 1, page_size: 20 },
    })
    return response.data
  },
  async createSession(source: SessionSource): Promise<ApiResponse<Session>> {
    if (useMock) {
      const mockApi = await import('../mocks/mockApi')
      return mockApi.createSession(source)
    }
    const response = await api.post<ApiResponse<Session>>('/sessions', { source })
    return response.data
  },
  async getSessionDetail(sessionId: string): Promise<ApiResponse<SessionDetail>> {
    if (useMock) {
      const mockApi = await import('../mocks/mockApi')
      return mockApi.getSessionDetail(sessionId)
    }
    const response = await api.get<ApiResponse<SessionDetail>>(`/sessions/${sessionId}`)
    return response.data
  },
  async deleteSession(sessionId: string): Promise<ApiResponse<DeleteSessionResponse>> {
    if (useMock) {
      const mockApi = await import('../mocks/mockApi')
      return mockApi.deleteSession(sessionId)
    }
    const response = await api.delete<ApiResponse<DeleteSessionResponse>>(`/sessions/${sessionId}`)
    return response.data
  },
}
