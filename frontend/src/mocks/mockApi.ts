import {
  createAssistantBlocks,
  createAssistantContent,
  createDraftSession,
  createTraceForQuery,
  inferAgentLabel,
  mockConfigStatus,
  mockDataSourceStatus,
  mockMessagesBySession,
  mockSessions,
  mockTraces,
  type MockSessionEntity,
} from './mockData'
import type {
  ApiResponse,
  ChatQueryRequest,
  ChatQueryResponse,
  ChatRegenerateRequest,
  ConfigStatus,
  DataSourceStatus,
  DeleteSessionResponse,
  LayoutPreferences,
  Message,
  PageResult,
  RawTraceStepResponse,
  Session,
  SessionDetail,
  SessionSource,
  Trace,
} from '../types/api'

const wait = <T>(data: T): Promise<ApiResponse<T>> =>
  new Promise((resolve) => {
    window.setTimeout(() => resolve({ code: 200, message: 'success', data }), 120)
  })

let mockLayoutPreferences: LayoutPreferences = {
  sidebar_width: 230,
  sidebar_width_range: { min: 200, max: 420 },
  trace_panel_width: 488,
  trace_panel_width_range: { min: 380, max: 640 },
  updated_at: '2026-06-08T14:12:00+08:00',
}

const sessionDto = (session: MockSessionEntity): Session => ({
  id: session.id,
  title: session.title,
  title_source: session.title_source,
  is_draft: session.is_draft,
  source: session.source,
  created_at: session.created_at,
  updated_at: session.updated_at,
  last_message_preview: session.last_message_preview,
  last_trace_id: session.last_trace_id,
})

const messageDto = (message: Message): Message => ({
  id: message.id,
  session_id: message.session_id,
  role: message.role,
  content: message.content,
  rich_blocks: message.rich_blocks.map((block) => ({
    id: block.id,
    type: block.type,
    title: block.title,
    payload: block.payload,
    sources: block.sources.map((source) => ({ ...source })),
    risk_notice: block.risk_notice,
  })),
  trace_id: message.trace_id,
  created_at: message.created_at,
})

const traceDto = (trace: Trace): Trace => ({
  id: trace.id,
  session_id: trace.session_id,
  message_id: trace.message_id,
  user_query: trace.user_query,
  status: trace.status,
  steps: trace.steps.map((step) => ({
    step_id: step.step_id,
    step_index: step.step_index,
    name: step.name,
    node: step.node,
    status: step.status,
    latency_ms: step.latency_ms,
    summary: step.summary,
    detail_sections: step.detail_sections.map((section) => ({
      title: section.title,
      items: section.items.map((item) => ({ label: item.label, value: item.value })),
    })),
    input: { ...step.input },
    output: { ...step.output },
    raw_json: { ...step.raw_json },
    error: step.error,
  })),
  metadata: {
    total_latency_ms: trace.metadata.total_latency_ms,
    tool_calls_count: trace.metadata.tool_calls_count,
    quality_check_result: trace.metadata.quality_check_result,
    model_versions: trace.metadata.model_versions ? { ...trace.metadata.model_versions } : undefined,
  },
})

export async function getSessions(keyword = '', page = 1, pageSize = 20): Promise<ApiResponse<PageResult<Session>>> {
  const normalized = keyword.trim().toLowerCase()
  const filtered = mockSessions.filter((session) => {
    if (!normalized) return true
    return session.title.toLowerCase().includes(normalized) || session.agent_label.toLowerCase().includes(normalized)
  })
  return wait({
    items: filtered.slice((page - 1) * pageSize, page * pageSize).map(sessionDto),
    total: filtered.length,
    page,
    page_size: pageSize,
  })
}

export async function createSession(source: SessionSource): Promise<ApiResponse<Session>> {
  const session = createDraftSession(source)
  mockSessions.unshift(session)
  mockMessagesBySession[session.id] = []
  return wait(sessionDto(session))
}

export async function getSessionDetail(sessionId: string): Promise<ApiResponse<SessionDetail>> {
  const session = mockSessions.find((item) => item.id === sessionId) ?? mockSessions[0]
  return wait({
    session: sessionDto(session),
    messages: (mockMessagesBySession[session.id] ?? []).map(messageDto),
  })
}

export async function deleteSession(sessionId: string): Promise<ApiResponse<DeleteSessionResponse>> {
  const index = mockSessions.findIndex((item) => item.id === sessionId)
  const deleted = index >= 0
  if (deleted) {
    mockSessions.splice(index, 1)
  }
  delete mockMessagesBySession[sessionId]
  Object.entries(mockTraces).forEach(([traceId, trace]) => {
    if (trace.session_id === sessionId) {
      delete mockTraces[traceId]
    }
  })
  return wait({ id: sessionId, deleted })
}

export async function postChatQuery(request: ChatQueryRequest): Promise<ApiResponse<ChatQueryResponse>> {
  const session = mockSessions.find((item) => item.id === request.session_id) ?? createDraftSession(request.source)
  if (!mockSessions.some((item) => item.id === session.id)) {
    mockSessions.unshift(session)
  }
  const isCalculator = request.query.includes('回报') || request.query.includes('收益') || request.query.includes('测算')
  const userMessage: Message = {
    id: `msg_${Date.now()}_user`,
    session_id: session.id,
    role: 'user',
    content: request.query,
    rich_blocks: [],
    trace_id: null,
    created_at: '2026-06-08T14:10:18+08:00',
  }
  const assistantMessage: Message = {
    id: `msg_${Date.now()}_assistant`,
    session_id: session.id,
    role: 'assistant',
    content: createAssistantContent(request.query),
    rich_blocks: createAssistantBlocks(request.query),
    trace_id: null,
    created_at: '2026-06-08T14:10:19+08:00',
  }
  const trace = createTraceForQuery(session.id, assistantMessage.id, request.query, isCalculator)
  mockTraces[trace.id] = trace
  assistantMessage.trace_id = trace.id

  session.title = request.query
  session.title_source = 'first_query'
  session.is_draft = false
  session.source = request.source
  session.updated_at = assistantMessage.created_at
  session.last_message_preview = assistantMessage.content
  session.last_trace_id = trace.id
  session.agent_label = inferAgentLabel(request.query)
  session.default_trace_id = trace.id
  mockMessagesBySession[session.id] = [userMessage, assistantMessage]

  return wait({
    session: sessionDto(session),
    user_message: messageDto(userMessage),
    assistant_message: messageDto(assistantMessage),
    trace: {
      id: trace.id,
      status: trace.status,
      metadata: {
        total_latency_ms: trace.metadata.total_latency_ms,
        tool_calls_count: trace.metadata.tool_calls_count,
        quality_check_result: trace.metadata.quality_check_result,
      },
    },
  })
}

export async function postChatRegenerateStream(
  request: ChatRegenerateRequest,
  handlers: { onEvent: (event: string, data: unknown) => void },
): Promise<void> {
  const session = mockSessions.find((item) => item.id === request.session_id)
  if (!session) {
    handlers.onEvent('error', { message: '会话不存在', code: 404 })
    return
  }

  const messages = mockMessagesBySession[request.session_id] ?? []
  const assistantIndex = messages.findIndex((item) => item.id === request.assistant_message_id)
  if (assistantIndex < 0) {
    handlers.onEvent('error', { message: '消息不存在', code: 404 })
    return
  }

  const assistant = messages[assistantIndex]
  if (assistant.role !== 'assistant') {
    handlers.onEvent('error', { message: '仅支持重新生成助手消息', code: 422 })
    return
  }

  let userMessage: Message | undefined
  for (let index = assistantIndex - 1; index >= 0; index -= 1) {
    if (messages[index].role === 'user') {
      userMessage = messages[index]
      break
    }
  }
  if (!userMessage) {
    handlers.onEvent('error', { message: '找不到配对的用户消息', code: 422 })
    return
  }

  handlers.onEvent('user_message', messageDto(userMessage))
  handlers.onEvent('session', sessionDto(session))
  handlers.onEvent('message_removed', { assistant_message_id: request.assistant_message_id })
  messages.splice(assistantIndex, 1)

  const isCalculator =
    userMessage.content.includes('回报') ||
    userMessage.content.includes('收益') ||
    userMessage.content.includes('测算')
  const assistantMessage: Message = {
    id: `msg_${Date.now()}_assistant`,
    session_id: session.id,
    role: 'assistant',
    content: createAssistantContent(userMessage.content),
    rich_blocks: createAssistantBlocks(userMessage.content),
    trace_id: null,
    created_at: '2026-06-08T14:10:19+08:00',
  }
  const trace = createTraceForQuery(session.id, assistantMessage.id, userMessage.content, isCalculator)
  mockTraces[trace.id] = trace
  assistantMessage.trace_id = trace.id
  messages.push(assistantMessage)

  session.updated_at = assistantMessage.created_at
  session.last_message_preview = assistantMessage.content
  session.last_trace_id = trace.id
  session.agent_label = inferAgentLabel(userMessage.content)
  session.default_trace_id = trace.id

  const response: ChatQueryResponse = {
    session: sessionDto(session),
    user_message: messageDto(userMessage),
    assistant_message: messageDto(assistantMessage),
    trace: {
      id: trace.id,
      status: trace.status,
      metadata: {
        total_latency_ms: trace.metadata.total_latency_ms,
        tool_calls_count: trace.metadata.tool_calls_count,
        quality_check_result: trace.metadata.quality_check_result,
      },
    },
  }

  handlers.onEvent('status', { phase: 'writing', label: 'Writing' })
  const content = assistantMessage.content
  const chunkSize = Math.max(4, Math.ceil(content.length / 24))
  for (let index = 0; index < content.length; index += chunkSize) {
    handlers.onEvent('content_delta', { delta: content.slice(index, index + chunkSize) })
    await new Promise((resolve) => setTimeout(resolve, 40))
  }
  handlers.onEvent('content_done', { content })
  handlers.onEvent('rich_blocks', { rich_blocks: assistantMessage.rich_blocks })
  handlers.onEvent('done', response)
}

export async function getTrace(traceId: string): Promise<ApiResponse<Trace>> {
  return wait(traceDto(mockTraces[traceId] ?? mockTraces.trace_20260608_001))
}

export async function getTraceStepRaw(traceId: string, stepId: string): Promise<ApiResponse<RawTraceStepResponse>> {
  const trace = mockTraces[traceId] ?? mockTraces.trace_20260608_001
  const step = trace.steps.find((item) => item.step_id === stepId) ?? trace.steps[0]
  return wait({
    trace_id: trace.id,
    step_id: step.step_id,
    raw_json: { ...step.raw_json },
  })
}

export async function getLayoutPreferences(): Promise<ApiResponse<LayoutPreferences>> {
  return wait({ ...mockLayoutPreferences })
}

export async function patchLayoutPreferences(sidebarWidth: number, tracePanelWidth: number): Promise<ApiResponse<LayoutPreferences>> {
  mockLayoutPreferences = {
    sidebar_width: sidebarWidth,
    sidebar_width_range: { min: 200, max: 420 },
    trace_panel_width: tracePanelWidth,
    trace_panel_width_range: { min: 380, max: 640 },
    updated_at: '2026-06-08T14:12:00+08:00',
  }
  return wait({ ...mockLayoutPreferences })
}

export async function getDataSourcesStatus(): Promise<ApiResponse<DataSourceStatus>> {
  return wait(mockDataSourceStatus)
}

export async function getConfigStatus(): Promise<ApiResponse<ConfigStatus>> {
  return wait(mockConfigStatus)
}
