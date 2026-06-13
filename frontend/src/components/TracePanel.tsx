import { useEffect, useMemo, useRef } from 'react'
import type { PointerEvent } from 'react'
import { useInvestmentStore } from '../stores/useInvestmentStore'
import { formatLatency } from '../utils/format'
import { sanitizeVisibleText } from '../utils/sanitizeResponse'

export function TracePanel() {
  const handleRef = useRef<HTMLDivElement | null>(null)
  const activeSessionId = useInvestmentStore((state) => state.activeSessionId)
  const sessions = useInvestmentStore((state) => state.sessions)
  const messagesBySession = useInvestmentStore((state) => state.messagesBySession)
  const tracesById = useInvestmentStore((state) => state.tracesById)
  const expandedStepIds = useInvestmentStore((state) => state.expandedStepIds)
  const pendingQuery = useInvestmentStore((state) => state.pendingQuery)
  const isQueryPending = pendingQuery?.sessionId === activeSessionId
  const loadTrace = useInvestmentStore((state) => state.loadTrace)
  const setTracePanelWidth = useInvestmentStore((state) => state.setTracePanelWidth)
  const persistLayout = useInvestmentStore((state) => state.persistLayout)
  const toggleStep = useInvestmentStore((state) => state.toggleStep)
  const openJson = useInvestmentStore((state) => state.openJson)

  const activeSession = sessions.find((session) => session.id === activeSessionId)
  const latestAssistantTraceId = [...(messagesBySession[activeSessionId] ?? [])]
    .reverse()
    .find((message) => message.role === 'assistant' && message.trace_id)?.trace_id
  const traceId = activeSession?.last_trace_id ?? latestAssistantTraceId ?? null
  const trace = traceId ? tracesById[traceId] : undefined
  const traceSteps = trace && 'steps' in trace ? trace.steps : []

  useEffect(() => {
    if (!traceId || isQueryPending) return
    const existing = tracesById[traceId]
    if (!existing || !('steps' in existing) || existing.steps.length === 0) {
      void loadTrace(traceId)
    }
  }, [traceId, tracesById, isQueryPending, loadTrace])

  const metricLatency = useMemo(() => (trace ? formatLatency(trace.metadata.total_latency_ms) : '--'), [trace])

  const startResize = (event: PointerEvent<HTMLDivElement>) => {
    const handle = handleRef.current
    if (!handle) return
    event.preventDefault()
    document.body.classList.add('is-trace-resizing')
    handle.setPointerCapture(event.pointerId)
    const onMove = (moveEvent: PointerEvent) => {
      setTracePanelWidth(window.innerWidth - moveEvent.clientX)
    }
    const onUp = () => {
      document.body.classList.remove('is-trace-resizing')
      void persistLayout()
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
      window.removeEventListener('pointercancel', onUp)
    }
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)
    window.addEventListener('pointercancel', onUp)
  }

  return (
    <aside className="trace-panel">
      <div ref={handleRef} className="trace-resize-handle" title="拖拽调整 Trace 面板宽度" onPointerDown={startResize} />
      <div className="trace-head">
        <h2>Trace 链路</h2>
        <p>{activeSession ? `${activeSession.title}` : '当前问答的节点流转、工具调用、RAG 命中和质检状态。'}</p>
        <div className="trace-metrics">
          <div className="trace-metric">
            <strong>{metricLatency}</strong>
            <span>总耗时</span>
          </div>
          <div className="trace-metric">
            <strong>{trace?.metadata.tool_calls_count ?? '--'}</strong>
            <span>工具调用</span>
          </div>
          <div className="trace-metric">
            <strong>{trace?.metadata.quality_check_result ?? '--'}</strong>
            <span>质检</span>
          </div>
        </div>
      </div>
      <div className="trace-scroll">
        {isQueryPending ? (
          <article className="trace-step open">
            <div className="step-line">
              <span className="dot running" />
              <div>
                <div className="step-head">
                  <span className="step-title">Trace 生成中</span>
                </div>
                <p>问答完成后将自动展示本次链路节点。</p>
              </div>
            </div>
          </article>
        ) : null}
        {!isQueryPending && trace && traceSteps.length === 0 ? (
          <article className="trace-step open">
            <div className="step-line">
              <span className="dot" />
              <div>
                <div className="step-head">
                  <span className="step-title">基础 Trace 摘要</span>
                  <span className="step-time">{metricLatency}</span>
                </div>
                <p>质检 {trace.metadata.quality_check_result}，工具调用 {trace.metadata.tool_calls_count} 次。</p>
              </div>
            </div>
          </article>
        ) : null}
        {traceSteps.map((step) => {
          const isOpen = expandedStepIds.includes(step.step_id)
          return (
            <article key={step.step_id} className={`trace-step ${isOpen ? 'open' : ''}`} onClick={() => toggleStep(step.step_id)}>
              <div className="step-line">
                <span className={`dot ${step.status === 'running' ? 'running' : ''}`} />
                <div>
                  <div className="step-head">
                    <span className="step-title">Step {step.step_index} {step.name}</span>
                    <span className="step-time">{formatLatency(step.latency_ms)}</span>
                  </div>
                  <p>{sanitizeVisibleText(step.summary)}</p>
                  {isOpen && (
                    <div className="step-detail">
                      {step.detail_sections.map((section) => (
                        <div key={section.title} className="kv">
                          {section.items.map((item) => (
                            <div key={`${section.title}-${item.label}`} className="kv-row">
                              <b>{sanitizeVisibleText(item.label)}</b>
                              <span>{sanitizeVisibleText(item.value)}</span>
                            </div>
                          ))}
                        </div>
                      ))}
                      <button
                        className="json-button"
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation()
                          void openJson(trace.id, step.step_id, `Step ${step.step_index} ${step.name}`)
                        }}
                      >
                        查看完整 JSON
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </article>
          )
        })}
      </div>
    </aside>
  )
}
