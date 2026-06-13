import type { Message } from '../types/api'

/** Build plain text for clipboard from an assistant message. */
export function buildCopyableMessageText(message: Message): string {
  return message.content.trim()
}
