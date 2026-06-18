import axios from 'axios'

const TRANSIENT_STATUS = new Set([502, 503, 504])

export function isTransientBackendError(error: unknown): boolean {
  if (!axios.isAxiosError(error)) {
    const message = error instanceof Error ? error.message : String(error)
    return /failed|fetch|network|ECONNREFUSED|Load failed/i.test(message)
  }
  if (!error.response) {
    return true
  }
  return TRANSIENT_STATUS.has(error.response.status)
}

export async function withBackendRetry<T>(
  operation: () => Promise<T>,
  options?: { attempts?: number; delayMs?: number },
): Promise<T> {
  const attempts = options?.attempts ?? 12
  const delayMs = options?.delayMs ?? 500

  let lastError: unknown
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      return await operation()
    } catch (error) {
      lastError = error
      if (!isTransientBackendError(error) || attempt === attempts - 1) {
        throw error
      }
      await new Promise((resolve) => setTimeout(resolve, delayMs))
    }
  }
  throw lastError
}
