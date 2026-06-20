const STORAGE_KEY = 'tide_demo_visitor_id'

function createVisitorId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `demo-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function getDemoVisitorId(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  const existing = window.localStorage.getItem(STORAGE_KEY)?.trim()
  if (existing) {
    return existing
  }
  const created = createVisitorId()
  window.localStorage.setItem(STORAGE_KEY, created)
  return created
}

export const DEMO_VISITOR_HEADER = 'X-Demo-Visitor-Id'

export function demoVisitorHeaders(): Record<string, string> {
  const visitorId = getDemoVisitorId()
  if (!visitorId) {
    return {}
  }
  return { [DEMO_VISITOR_HEADER]: visitorId }
}
