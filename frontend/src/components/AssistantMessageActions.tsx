import { useState } from 'react'
import type { Message } from '../types/api'
import { buildCopyableMessageText } from '../utils/messageCopyText'

interface AssistantMessageActionsProps {
  message: Message
  disabled?: boolean
  onCopy?: () => void
  onRegenerate?: () => void
  onFeedback?: () => void
}

export function AssistantMessageActions({
  message,
  disabled = false,
  onCopy,
  onRegenerate,
  onFeedback,
}: AssistantMessageActionsProps) {
  const [copied, setCopied] = useState(false)
  const [feedbackShown, setFeedbackShown] = useState(false)

  const handleCopy = async () => {
    if (disabled) return
    const text = buildCopyableMessageText(message)
    if (!text) return
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      onCopy?.()
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      window.alert('复制失败，请手动选择文本复制。')
    }
  }

  const handleRegenerate = () => {
    if (disabled) return
    onRegenerate?.()
  }

  const handleFeedback = () => {
    if (disabled) return
    setFeedbackShown(true)
    onFeedback?.()
    window.setTimeout(() => setFeedbackShown(false), 2000)
  }

  return (
    <div className="assistant-message-actions">
      <button type="button" className="action-btn" disabled={disabled} onClick={() => void handleCopy()}>
        {copied ? '已复制' : '复制'}
      </button>
      <button type="button" className="action-btn" disabled={disabled} onClick={handleRegenerate}>
        重新生成
      </button>
      <button type="button" className="action-btn" disabled={disabled} onClick={handleFeedback}>
        {feedbackShown ? '感谢反馈，功能即将上线' : '提交反馈'}
      </button>
    </div>
  )
}
