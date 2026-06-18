import { useInvestmentStore } from '../stores/useInvestmentStore'

/** True when client chat view has no user messages yet (new / draft session). */
export function useEmptyClientChat(): boolean {
  const mode = useInvestmentStore((state) => state.mode)
  const view = useInvestmentStore((state) => state.view)
  const activeSessionId = useInvestmentStore((state) => state.activeSessionId)
  const messagesBySession = useInvestmentStore((state) => state.messagesBySession)
  const pendingQuery = useInvestmentStore((state) => state.pendingQuery)

  if (mode !== 'client' || view !== 'chat') {
    return false
  }

  const messages = activeSessionId ? (messagesBySession[activeSessionId] ?? []) : []
  const hasUserMessage = messages.some((message) => message.role === 'user')
  const isPending = pendingQuery?.sessionId === activeSessionId

  return !hasUserMessage && !isPending
}
