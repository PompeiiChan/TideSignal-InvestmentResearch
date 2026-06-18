import { api } from './api'
import type {
  ApiResponse,
  ChatQueryRequest,
  ChatQueryResponse,
  ChatRegenerateRequest,
} from '../types/api'

const useMock = import.meta.env.VITE_USE_MOCK === 'true'
const apiBase = import.meta.env.VITE_API_BASE_URL || '/api'

export type ChatStreamHandlers = {
  onEvent: (event: string, data: unknown) => void
  signal?: AbortSignal
}

function parseSseChunk(chunk: string): { event: string; data: unknown } | null {
  let event = 'message'
  let dataRaw = ''
  for (const line of chunk.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataRaw += line.slice(5).trim()
    }
  }
  if (!dataRaw) return null
  return { event, data: JSON.parse(dataRaw) as unknown }
}

async function consumeSseResponse(response: Response, handlers: ChatStreamHandlers): Promise<void> {
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { message?: string } | null
    throw new Error(body?.message || `请求失败 (${response.status})`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('无法读取流式响应')
  }

  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''
    for (const part of parts) {
      const parsed = parseSseChunk(part.trim())
      if (parsed) {
        handlers.onEvent(parsed.event, parsed.data)
      }
    }
  }
  const tail = buffer.trim()
  if (tail) {
    const parsed = parseSseChunk(tail)
    if (parsed) {
      handlers.onEvent(parsed.event, parsed.data)
    }
  }
}

async function simulateQueryStream(response: ApiResponse<ChatQueryResponse>, handlers: ChatStreamHandlers): Promise<void> {
  const emitStep = (stepId: string, label: string, parentId?: string) => {
    handlers.onEvent('step_start', {
      step: {
        step_id: stepId,
        status: 'running',
        label,
        ...(parentId ? { parent_id: parentId } : {}),
      },
    })
  }
  const completeStep = (stepId: string) => {
    handlers.onEvent('step_complete', { step_id: stepId })
  }

  handlers.onEvent('user_message', response.data.user_message)
  handlers.onEvent('session', response.data.session)

  emitStep('understand_query', '正在理解您的问题')
  await new Promise((resolve) => setTimeout(resolve, 120))
  completeStep('understand_query')

  emitStep('recognize_intent', '正在识别问题类型')
  await new Promise((resolve) => setTimeout(resolve, 120))
  completeStep('recognize_intent')

  emitStep('match_expert', '正在匹配投研专家 · 问股分析')
  completeStep('match_expert')

  emitStep('fetch_materials', '正在获取相关资料')
  await new Promise((resolve) => setTimeout(resolve, 100))
  completeStep('fetch_materials')

  emitStep('quality_review', '正在审核回答质量')
  await new Promise((resolve) => setTimeout(resolve, 80))
  completeStep('quality_review')

  emitStep('generate_answer', '正在生成回答')
  await new Promise((resolve) => setTimeout(resolve, 80))

  handlers.onEvent('response_stream_start', { summary: '问股分析 · 2 项资料' })
  completeStep('generate_answer')

  const content = response.data.assistant_message.content
  const chunkSize = Math.max(4, Math.ceil(content.length / 24))
  for (let index = 0; index < content.length; index += chunkSize) {
    handlers.onEvent('content_delta', { delta: content.slice(index, index + chunkSize) })
    await new Promise((resolve) => setTimeout(resolve, 40))
  }
  handlers.onEvent('content_done', { content })
  handlers.onEvent('rich_blocks', { rich_blocks: response.data.assistant_message.rich_blocks })
  handlers.onEvent('done', response.data)
}

export const chatService = {
  async postChatQuery(request: ChatQueryRequest): Promise<ApiResponse<ChatQueryResponse>> {
    if (useMock) {
      const mockApi = await import('../mocks/mockApi')
      return mockApi.postChatQuery(request)
    }
    const response = await api.post<ApiResponse<ChatQueryResponse>>('/chat/query', request, {
      timeout: 120000,
    })
    return response.data
  },

  async postChatQueryStream(request: ChatQueryRequest, handlers: ChatStreamHandlers): Promise<void> {
    if (useMock) {
      const mockApi = await import('../mocks/mockApi')
      const response = await mockApi.postChatQuery(request)
      await simulateQueryStream(response, handlers)
      return
    }

    const response = await fetch(`${apiBase}/chat/query/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(request),
      signal: handlers.signal,
    })
    await consumeSseResponse(response, handlers)
  },

  async postChatRegenerateStream(request: ChatRegenerateRequest, handlers: ChatStreamHandlers): Promise<void> {
    if (useMock) {
      const mockApi = await import('../mocks/mockApi')
      await mockApi.postChatRegenerateStream(request, handlers)
      return
    }

    const response = await fetch(`${apiBase}/chat/regenerate/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(request),
      signal: handlers.signal,
    })
    await consumeSseResponse(response, handlers)
  },
}
