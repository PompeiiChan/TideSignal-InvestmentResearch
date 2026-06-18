import { create } from 'zustand'
import { investmentService } from '../services/investmentService'
import type {
  ChatQueryResponse,
  ConfigStatus,
  DataSourceStatus,
  Message,
  RichBlock,
  Session,
  SessionSource,
  Trace,
  TraceSummary,
} from '../types/api'
import { clamp } from '../utils/format'
import { extractRichBlockTypes } from '../utils/richBlockLabels'
import { sanitizeMessage, sanitizeMessages, sanitizeSession } from '../utils/sanitizeResponse'

export type ViewMode = 'client' | 'admin'
export type AppView = 'chat' | 'data' | 'settings'

function resolveClientView(view: AppView): AppView {
  return view === 'settings' || view === 'data' ? 'chat' : view
}

const DEFAULT_SIDEBAR_WIDTH = 230
const LEGACY_SIDEBAR_WIDTHS = new Set([288, 420])

function normalizeSidebarWidth(width: number): number {
  if (LEGACY_SIDEBAR_WIDTHS.has(width)) {
    return DEFAULT_SIDEBAR_WIDTH
  }
  return width
}
export type StoredTrace = Trace | TraceSummary

let searchRequestSeq = 0

function hasTraceSteps(trace: StoredTrace | null | undefined): trace is Trace {
  return Boolean(trace && 'steps' in trace)
}

function needsTraceDetails(trace: StoredTrace | null | undefined): boolean {
  return Boolean(trace && !hasTraceSteps(trace))
}

function defaultExpandedStepIds(trace: StoredTrace | null | undefined): string[] {
  if (!hasTraceSteps(trace)) return []
  return [trace.steps[1]?.step_id ?? trace.steps[0]?.step_id ?? ''].filter(Boolean)
}

function fallbackTraceSummary(traceId: string): TraceSummary {
  return {
    id: traceId,
    status: 'success',
    metadata: {
      total_latency_ms: 0,
      tool_calls_count: 0,
      quality_check_result: 'PASS',
      model_versions: {
        master_bot: 'local-master',
        response_builder: 'local-response-builder',
      },
    },
  }
}

async function tryGetTrace(traceId: string): Promise<StoredTrace> {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const response = await investmentService.getTrace(traceId)
      if (hasTraceSteps(response.data)) return response.data
    } catch {
      // Trace may not be readable immediately after SSE done; retry briefly.
    }
    if (attempt < 2) {
      await new Promise((resolve) => setTimeout(resolve, 150 * (attempt + 1)))
    }
  }
  return fallbackTraceSummary(traceId)
}

function mergeSessionDuringQuery(incoming: Session, existing: Session | undefined): Session {
  if (!existing) return incoming
  return {
    ...incoming,
    last_trace_id: existing.last_trace_id,
  }
}

function applyChatQueryResult(
  set: (partial: ((state: InvestmentState) => Partial<InvestmentState>)) => void,
  payload: ChatQueryResponse,
  options?: { pendingUserId?: string; pendingAssistantId?: string },
) {
  const session = sanitizeSession(payload.session)
  const userMessage = sanitizeMessage(payload.user_message)
  const assistantMessage = {
    ...sanitizeMessage(payload.assistant_message),
    streaming: false,
    status_label: undefined,
  }
  const traceSummary = payload.trace

  set((current) => {
    const existing = current.messagesBySession[session.id] ?? []
    const withoutPending = existing.filter((message) => {
      if (options?.pendingUserId && message.id === options.pendingUserId) return false
      if (options?.pendingAssistantId && message.id === options.pendingAssistantId) return false
      return true
    })

    const userIndex = withoutPending.findIndex((message) => message.id === userMessage.id)
    const assistantIndex = withoutPending.findIndex(
      (message) => message.id === assistantMessage.id || message.id === options?.pendingAssistantId,
    )

    const nextMessages = [...withoutPending]
    if (userIndex >= 0) {
      nextMessages[userIndex] = userMessage
    } else {
      nextMessages.push(userMessage)
    }
    if (assistantIndex >= 0) {
      nextMessages[assistantIndex] = assistantMessage
    } else {
      nextMessages.push(assistantMessage)
    }

    const clearPending = current.pendingQuery?.sessionId === session.id

    return {
      pendingQuery: clearPending ? null : current.pendingQuery,
      sessions: [session, ...current.sessions.filter((item) => item.id !== session.id)],
      messagesBySession: {
        ...current.messagesBySession,
        [session.id]: nextMessages,
      },
      tracesById: { ...current.tracesById, [traceSummary.id]: traceSummary },
      expandedStepIds:
        current.activeSessionId === session.id
          ? defaultExpandedStepIds(traceSummary)
          : current.expandedStepIds,
    }
  })

  void (async () => {
    const fullTrace = await tryGetTrace(traceSummary.id)
    if (!hasTraceSteps(fullTrace)) return
    set((current) => ({
      tracesById: { ...current.tracesById, [fullTrace.id]: fullTrace },
      expandedStepIds: defaultExpandedStepIds(fullTrace),
    }))
  })()
}

function handleChatStreamEvent(
  set: (partial: ((state: InvestmentState) => Partial<InvestmentState>)) => void,
  get: () => InvestmentState,
  ctx: ChatStreamContext,
  event: string,
  data: unknown,
) {
  const { sessionId, pendingUserId, pendingAssistantId, streamFinishedRef } = ctx
  const updateAssistant = (patch: Partial<Message>) => {
    set((current) => ({
      messagesBySession: {
        ...current.messagesBySession,
        [sessionId]: (current.messagesBySession[sessionId] ?? []).map((message) =>
          message.id === pendingAssistantId ? { ...message, ...patch } : message,
        ),
      },
    }))
  }

  const setQueryStatus = (label: string) => {
    set((current) => ({
      pendingQuery: current.pendingQuery
        ? { ...current.pendingQuery, statusLabel: label }
        : current.pendingQuery,
    }))
  }

  const clearPendingQuery = () => {
    set((current) => ({
      pendingQuery: current.pendingQuery?.sessionId === sessionId ? null : current.pendingQuery,
    }))
  }

  const failAssistant = (message: string) => {
    updateAssistant({
      content: message,
      streaming: false,
      status_label: undefined,
    })
    clearPendingQuery()
  }

  if (event === 'message_removed') {
    const removedId = (data as { assistant_message_id?: string }).assistant_message_id
    if (removedId) {
      set((current) => ({
        messagesBySession: {
          ...current.messagesBySession,
          [sessionId]: (current.messagesBySession[sessionId] ?? []).filter(
            (message) => message.id !== removedId,
          ),
        },
      }))
    }
    return
  }

  if (event === 'user_message') {
    if (!pendingUserId) return
    const userMessage = sanitizeMessage(data as Message)
    set((current) => ({
      messagesBySession: {
        ...current.messagesBySession,
        [sessionId]: (current.messagesBySession[sessionId] ?? []).map((message) =>
          message.id === pendingUserId ? userMessage : message,
        ),
      },
    }))
    setQueryStatus('Thinking')
    updateAssistant({ status_label: 'Thinking', streaming: true })
    return
  }

  if (event === 'session') {
    const session = sanitizeSession(data as Session)
    set((current) => {
      const existing = current.sessions.find((item) => item.id === session.id)
      const merged =
        current.pendingQuery?.sessionId === session.id ? mergeSessionDuringQuery(session, existing) : session
      return {
        sessions: [merged, ...current.sessions.filter((item) => item.id !== session.id)],
      }
    })
    return
  }

  if (event === 'status') {
    const status = data as { label?: string; phase?: string }
    const label = status.label ?? 'Thinking'
    setQueryStatus(label)
    updateAssistant({ status_label: label, streaming: true })
    return
  }

  if (event === 'content_delta') {
    const delta = (data as { delta?: string }).delta ?? ''
    const currentAssistant = get().messagesBySession[sessionId]?.find(
      (message) => message.id === pendingAssistantId,
    )
    const label = 'Writing'
    setQueryStatus(label)
    updateAssistant({
      content: `${currentAssistant?.content ?? ''}${delta}`,
      streaming: true,
      status_label: label,
      content_complete: false,
    })
    return
  }

  if (event === 'content_reset') {
    setQueryStatus('Rewriting')
    updateAssistant({
      content: '',
      streaming: true,
      status_label: 'Rewriting',
      content_complete: false,
    })
    return
  }

  if (event === 'content_done') {
    const doneContent = (data as { content?: string }).content
    const currentAssistant = get().messagesBySession[sessionId]?.find(
      (message) => message.id === pendingAssistantId,
    )
    updateAssistant({
      content: doneContent ?? currentAssistant?.content ?? '',
      content_complete: true,
      streaming: true,
    })
    return
  }

  if (event === 'rich_blocks') {
    const richBlocks = (data as { rich_blocks?: RichBlock[] }).rich_blocks ?? []
    const richBlockTypes = extractRichBlockTypes(richBlocks)
    updateAssistant({ rich_blocks: richBlocks, streaming: true })
    set((current) => ({
      sessions: current.sessions.map((session) =>
        session.id === sessionId ? { ...session, rich_block_types: richBlockTypes } : session,
      ),
    }))
    return
  }

  if (event === 'error') {
    const errorData = data as { message?: string }
    failAssistant(errorData.message ?? '请求失败，请稍后重试。')
    streamFinishedRef.current = true
    return
  }

  if (event === 'done') {
    streamFinishedRef.current = true
    applyChatQueryResult(set, data as ChatQueryResponse, {
      pendingUserId,
      pendingAssistantId,
    })
  }
}

async function runChatStream(
  set: (partial: ((state: InvestmentState) => Partial<InvestmentState>)) => void,
  get: () => InvestmentState,
  ctx: ChatStreamContext,
  streamCall: (handlers: { onEvent: (event: string, data: unknown) => void }) => Promise<void>,
) {
  const { sessionId, pendingAssistantId } = ctx
  const streamFinishedRef = ctx.streamFinishedRef

  const updateAssistant = (patch: Partial<Message>) => {
    set((current) => ({
      messagesBySession: {
        ...current.messagesBySession,
        [sessionId]: (current.messagesBySession[sessionId] ?? []).map((message) =>
          message.id === pendingAssistantId ? { ...message, ...patch } : message,
        ),
      },
    }))
  }

  const clearPendingQuery = () => {
    set((current) => ({
      pendingQuery: current.pendingQuery?.sessionId === sessionId ? null : current.pendingQuery,
    }))
  }

  const failAssistant = (message: string) => {
    updateAssistant({
      content: message,
      streaming: false,
      status_label: undefined,
    })
    clearPendingQuery()
  }

  try {
    await streamCall({
      onEvent: (event, data) => {
        try {
          handleChatStreamEvent(set, get, ctx, event, data)
        } catch (handlerError) {
          console.error('chat stream handler error', handlerError)
          failAssistant('处理回答时出错，请刷新后重试。')
          streamFinishedRef.current = true
        }
      },
    })

    if (!streamFinishedRef.current && get().pendingQuery?.sessionId === sessionId) {
      const currentAssistant = get().messagesBySession[sessionId]?.find(
        (message) => message.id === pendingAssistantId,
      )
      if (currentAssistant?.content.trim()) {
        updateAssistant({ streaming: false, status_label: undefined })
        clearPendingQuery()
      } else {
        failAssistant('回答未完成，请稍后重试。')
      }
    }
  } catch (error) {
    const currentAssistant = get().messagesBySession[sessionId]?.find(
      (message) => message.id === pendingAssistantId,
    )
    set((current) => ({
      pendingQuery: current.pendingQuery?.sessionId === sessionId ? null : current.pendingQuery,
      messagesBySession: {
        ...current.messagesBySession,
        [sessionId]: (current.messagesBySession[sessionId] ?? []).map((message) => {
          if (message.id === pendingAssistantId) {
            return {
              ...message,
              streaming: false,
              status_label: undefined,
              content: currentAssistant?.content.trim()
                ? currentAssistant.content
                : '网络或服务异常，请稍后重试。',
            }
          }
          return message
        }),
      },
    }))
    throw error
  }
}

interface JsonModalState {
  title: string
  data: Record<string, unknown>
}

interface PendingQueryState {
  sessionId: string
  pendingUserId?: string
  pendingAssistantId: string
  regeneratingAssistantId?: string
  statusLabel: string
}

interface ChatStreamContext {
  sessionId: string
  pendingUserId?: string
  pendingAssistantId: string
  streamFinishedRef: { current: boolean }
}

interface InvestmentState {
  initialized: boolean
  mode: ViewMode
  view: AppView
  sessions: Session[]
  activeSessionId: string
  messagesBySession: Record<string, Message[]>
  tracesById: Record<string, StoredTrace>
  searchKeyword: string
  sidebarWidth: number
  tracePanelWidth: number
  expandedStepIds: string[]
  jsonModal: JsonModalState | null
  dataSources: DataSourceStatus | null
  configStatus: ConfigStatus | null
  pendingQuery: PendingQueryState | null
  initialize: (mode: ViewMode, view: AppView) => Promise<void>
  setMode: (mode: ViewMode) => void
  setView: (view: AppView) => void
  setSearchKeyword: (keyword: string) => Promise<void>
  createSession: (source: SessionSource) => Promise<void>
  selectSession: (sessionId: string) => Promise<void>
  deleteSession: (sessionId: string) => Promise<void>
  sendQuery: (query: string) => Promise<void>
  regenerateMessage: (assistantMessageId: string) => Promise<void>
  loadTrace: (traceId: string) => Promise<void>
  loadDataSources: () => Promise<void>
  loadConfigStatus: () => Promise<void>
  setSidebarWidth: (width: number) => void
  setTracePanelWidth: (width: number) => void
  persistLayout: () => Promise<void>
  toggleStep: (stepId: string) => void
  openJson: (traceId: string, stepId: string, title: string) => Promise<void>
  closeJson: () => void
}

export const useInvestmentStore = create<InvestmentState>((set, get) => ({
  initialized: false,
  mode: 'client',
  view: 'chat',
  sessions: [],
  activeSessionId: '',
  messagesBySession: {},
  tracesById: {},
  searchKeyword: '',
  sidebarWidth: 230,
  tracePanelWidth: 488,
  expandedStepIds: ['step_002'],
  jsonModal: null,
  dataSources: null,
  configStatus: null,
  pendingQuery: null,
  async initialize(mode, view) {
    const resolvedView = mode === 'client' ? resolveClientView(view) : view
    set({ mode, view: resolvedView })
    if (get().initialized) return
    set({ messagesBySession: {} })
    const [sessionsResponse, layoutResponse] = await Promise.all([
      investmentService.getSessions(''),
      investmentService.getLayoutPreferences(),
    ])
    const sessions = sessionsResponse.data.items.map(sanitizeSession)
    const firstSession = sessions[0]
    const detailResponse = firstSession ? await investmentService.getSessionDetail(firstSession.id) : null
    const traceId = detailResponse?.data.session.last_trace_id
    const trace = traceId ? await tryGetTrace(traceId) : null
    const sidebarWidth = normalizeSidebarWidth(layoutResponse.data.sidebar_width)
    const tracePanelWidth = layoutResponse.data.trace_panel_width
    if (sidebarWidth !== layoutResponse.data.sidebar_width) {
      void investmentService.patchLayoutPreferences(sidebarWidth, tracePanelWidth)
    }
    set({
      initialized: true,
      sessions,
      activeSessionId: firstSession?.id ?? '',
      messagesBySession: firstSession && detailResponse ? { [firstSession.id]: sanitizeMessages(detailResponse.data.messages) } : {},
      tracesById: trace ? { [trace.id]: trace } : {},
      sidebarWidth,
      tracePanelWidth,
    })
    if (mode === 'admin' && resolvedView === 'data') void get().loadDataSources()
    if (mode === 'admin' && resolvedView === 'settings') void get().loadConfigStatus()
  },
  setMode(mode) {
    set((state) => ({
      mode,
      view: mode === 'client' ? resolveClientView(state.view) : state.view,
    }))
    if (mode === 'admin') {
      const { activeSessionId, sessions, tracesById } = get()
      const session = sessions.find((item) => item.id === activeSessionId)
      const traceId = session?.last_trace_id
      if (traceId) {
        const existing = tracesById[traceId]
        if (!existing || needsTraceDetails(existing)) {
          void get().loadTrace(traceId)
        }
      }
    }
  },
  setView(view) {
    set((state) => ({
      view: state.mode === 'client' ? 'chat' : view,
    }))
    const { mode } = get()
    if (mode === 'admin' && view === 'data') void get().loadDataSources()
    if (mode === 'admin' && view === 'settings') void get().loadConfigStatus()
  },
  async setSearchKeyword(keyword) {
    const requestSeq = searchRequestSeq + 1
    searchRequestSeq = requestSeq
    set({ searchKeyword: keyword })
    const response = await investmentService.getSessions(keyword)
    if (requestSeq !== searchRequestSeq) return
    set({ sessions: response.data.items.map(sanitizeSession) })
  },
  async createSession(source) {
    const response = await investmentService.createSession(source)
    const session = sanitizeSession(response.data)
    const detailResponse = await investmentService.getSessionDetail(session.id)
    set((state) => ({
      sessions: [session, ...state.sessions.filter((item) => item.id !== session.id)],
      activeSessionId: session.id,
      messagesBySession: { ...state.messagesBySession, [session.id]: sanitizeMessages(detailResponse.data.messages) },
      view: 'chat',
    }))
  },
  async selectSession(sessionId) {
    const pending = get().pendingQuery
    if (pending?.sessionId === sessionId) {
      const session = get().sessions.find((item) => item.id === sessionId)
      const traceId = session?.last_trace_id
      const existingTrace = traceId ? get().tracesById[traceId] : null
      const loadedTrace =
        traceId && (!existingTrace || needsTraceDetails(existingTrace)) ? await tryGetTrace(traceId) : null
      const trace = existingTrace ?? loadedTrace
      set((state) => ({
        activeSessionId: sessionId,
        tracesById: loadedTrace ? { ...state.tracesById, [loadedTrace.id]: loadedTrace } : state.tracesById,
        expandedStepIds: trace ? defaultExpandedStepIds(trace) : state.expandedStepIds,
        view: 'chat',
      }))
      return
    }

    const detailResponse = await investmentService.getSessionDetail(sessionId)
    const traceId = detailResponse.data.session.last_trace_id
    const existingTrace = traceId ? get().tracesById[traceId] : null
    const loadedTrace = traceId && (!existingTrace || needsTraceDetails(existingTrace)) ? await tryGetTrace(traceId) : null
    const trace = existingTrace ?? loadedTrace
    set((state) => ({
      activeSessionId: sessionId,
      messagesBySession: { ...state.messagesBySession, [sessionId]: sanitizeMessages(detailResponse.data.messages) },
      tracesById: loadedTrace ? { ...state.tracesById, [loadedTrace.id]: loadedTrace } : state.tracesById,
      expandedStepIds: trace ? defaultExpandedStepIds(trace) : state.expandedStepIds,
      view: 'chat',
    }))
  },
  async deleteSession(sessionId) {
    await investmentService.deleteSession(sessionId)
    const state = get()
    const sessions = state.sessions.filter((session) => session.id !== sessionId)
    const messagesBySession = { ...state.messagesBySession }
    delete messagesBySession[sessionId]
    const deletedTraceId = state.sessions.find((session) => session.id === sessionId)?.last_trace_id
    const tracesById = Object.fromEntries(
      Object.entries(state.tracesById).filter(([traceId, trace]) => {
        if (traceId === deletedTraceId) return false
        return !hasTraceSteps(trace) || trace.session_id !== sessionId
      }),
    )

    if (state.activeSessionId !== sessionId) {
      set({ sessions, messagesBySession, tracesById })
      return
    }

    const nextSession = sessions[0]
    if (!nextSession) {
      set({
        sessions,
        activeSessionId: '',
        messagesBySession,
        tracesById,
        expandedStepIds: [],
        jsonModal: null,
      })
      return
    }

    const detailResponse = await investmentService.getSessionDetail(nextSession.id)
    const traceId = detailResponse.data.session.last_trace_id
    const trace = traceId ? tracesById[traceId] ?? (await tryGetTrace(traceId)) : null
    set({
      sessions,
      activeSessionId: nextSession.id,
      messagesBySession: { ...messagesBySession, [nextSession.id]: sanitizeMessages(detailResponse.data.messages) },
      tracesById: trace ? { ...tracesById, [trace.id]: trace } : tracesById,
      expandedStepIds: defaultExpandedStepIds(trace),
      jsonModal: null,
      view: 'chat',
    })
  },
  async sendQuery(query) {
    let activeSessionId = get().activeSessionId
    if (get().pendingQuery?.sessionId === activeSessionId) return
    if (!activeSessionId) {
      await get().createSession(get().mode)
      activeSessionId = get().activeSessionId
    }
    if (!activeSessionId) return

    const state = get()
    const now = new Date().toISOString()
    const pendingUserId = `pending_user_${Date.now()}`
    const pendingAssistantId = `pending_assistant_${Date.now()}`
    const initialStatus = 'Thinking'
    const optimisticUser: Message = {
      id: pendingUserId,
      session_id: activeSessionId,
      role: 'user',
      content: query,
      rich_blocks: [],
      trace_id: null,
      created_at: now,
    }
    const optimisticAssistant: Message = {
      id: pendingAssistantId,
      session_id: activeSessionId,
      role: 'assistant',
      content: '',
      rich_blocks: [],
      trace_id: null,
      created_at: now,
      streaming: true,
      status_label: initialStatus,
    }

    set((current) => ({
      pendingQuery: {
        sessionId: activeSessionId,
        pendingUserId,
        pendingAssistantId,
        statusLabel: initialStatus,
      },
      messagesBySession: {
        ...current.messagesBySession,
        [activeSessionId]: [...(current.messagesBySession[activeSessionId] ?? []), optimisticUser, optimisticAssistant],
      },
    }))

    const streamFinishedRef = { current: false }
    await runChatStream(
      set,
      get,
      {
        sessionId: activeSessionId,
        pendingUserId,
        pendingAssistantId,
        streamFinishedRef,
      },
      (handlers) =>
        investmentService.postChatQueryStream(
          { session_id: activeSessionId, source: state.mode, query },
          handlers,
        ),
    )
  },
  async regenerateMessage(assistantMessageId) {
    const activeSessionId = get().activeSessionId
    if (!activeSessionId || get().pendingQuery?.sessionId === activeSessionId) return

    const messages = get().messagesBySession[activeSessionId] ?? []
    const assistantIndex = messages.findIndex((message) => message.id === assistantMessageId)
    if (assistantIndex < 0) return

    const now = new Date().toISOString()
    const pendingAssistantId = `pending_assistant_${Date.now()}`
    const initialStatus = 'Thinking'
    const optimisticAssistant: Message = {
      id: pendingAssistantId,
      session_id: activeSessionId,
      role: 'assistant',
      content: '',
      rich_blocks: [],
      trace_id: null,
      created_at: now,
      streaming: true,
      status_label: initialStatus,
    }

    set((current) => ({
      pendingQuery: {
        sessionId: activeSessionId,
        pendingAssistantId,
        regeneratingAssistantId: assistantMessageId,
        statusLabel: initialStatus,
      },
      messagesBySession: {
        ...current.messagesBySession,
        [activeSessionId]: messages.map((message, index) =>
          index === assistantIndex ? optimisticAssistant : message,
        ),
      },
    }))

    const streamFinishedRef = { current: false }
    await runChatStream(
      set,
      get,
      {
        sessionId: activeSessionId,
        pendingAssistantId,
        streamFinishedRef,
      },
      (handlers) =>
        investmentService.postChatRegenerateStream(
          {
            session_id: activeSessionId,
            assistant_message_id: assistantMessageId,
            source: get().mode,
          },
          handlers,
        ),
    )
  },
  async loadTrace(traceId) {
    const trace = await tryGetTrace(traceId)
    set((state) => ({
      tracesById: { ...state.tracesById, [traceId]: trace },
      expandedStepIds: hasTraceSteps(trace) ? defaultExpandedStepIds(trace) : state.expandedStepIds,
    }))
  },
  async loadDataSources() {
    const response = await investmentService.getDataSourcesStatus()
    set({ dataSources: response.data })
  },
  async loadConfigStatus() {
    if (get().mode !== 'admin') return
    const response = await investmentService.getConfigStatus()
    set({ configStatus: response.data })
  },
  setSidebarWidth(width) {
    set({ sidebarWidth: clamp(width, 200, 420) })
  },
  setTracePanelWidth(width) {
    set({ tracePanelWidth: clamp(width, 380, 640) })
  },
  async persistLayout() {
    const state = get()
    await investmentService.patchLayoutPreferences(state.sidebarWidth, state.tracePanelWidth)
  },
  toggleStep(stepId) {
    set((state) => ({
      expandedStepIds: state.expandedStepIds.includes(stepId)
        ? state.expandedStepIds.filter((id) => id !== stepId)
        : [...state.expandedStepIds, stepId],
    }))
  },
  async openJson(traceId, stepId, title) {
    const response = await investmentService.getTraceStepRaw(traceId, stepId)
    set({ jsonModal: { title, data: response.data.raw_json } })
  },
  closeJson() {
    set({ jsonModal: null })
  },
}))
