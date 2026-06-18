import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { AssistantMessageActions } from './AssistantMessageActions'
import { MarkdownContent } from './MarkdownContent'
import { RichBlockRenderer } from './RichBlockRenderer'
import { TideSignalAnimatedLogo } from './TideSignalAnimatedLogo'
import { useEmptyClientChat } from '../hooks/useEmptyClientChat'
import { useMarketGreeting } from '../hooks/useMarketGreeting'
import { useInvestmentStore } from '../stores/useInvestmentStore'
import { sanitizeMessage } from '../utils/sanitizeResponse'

const EMPTY_MESSAGES: ReturnType<typeof sanitizeMessage>[] = []

const COMPOSER_PLACEHOLDER = '说个你关心的股票或方向，我帮你理理。'

const QUICK_PROMPTS = [
  '中际旭创基本面怎么样，业绩可持续吗？',
  '今天涨幅靠前的半导体有哪些？',
  '帮我看一下今天A股行业板块热力图',
  '宁德时代现在估值贵不贵？',
]

interface ComposerProps {
  query: string
  disabled: boolean
  variant: 'default' | 'hero'
  onChange: (value: string) => void
  onSubmit: () => void
}

function Composer({ query, disabled, variant, onChange, onSubmit }: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      onSubmit()
    }
  }

  return (
    <div className={`composer composer--${variant}`}>
      <div className="composer-inner">
        <div className="composer-box">
          <textarea
            ref={textareaRef}
            rows={variant === 'hero' ? 3 : 1}
            placeholder={COMPOSER_PLACEHOLDER}
            value={query}
            disabled={disabled}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            className="send"
            type="button"
            title="发送"
            disabled={!query.trim() || disabled}
            onClick={onSubmit}
          >
            {disabled ? '…' : '↑'}
          </button>
        </div>
        <div className="composer-note">系统仅提供信息整理、数据查询和参数测算，不构成投资建议。</div>
      </div>
    </div>
  )
}

export function ChatView() {
  const [query, setQuery] = useState('')
  const stackRef = useRef<HTMLDivElement | null>(null)
  const isEmptyClientChat = useEmptyClientChat()
  const marketGreeting = useMarketGreeting()
  const activeSessionId = useInvestmentStore((state) => state.activeSessionId)
  const messagesBySession = useInvestmentStore((state) => state.messagesBySession)
  const pendingQuery = useInvestmentStore((state) => state.pendingQuery)
  const isCurrentSessionPending = pendingQuery?.sessionId === activeSessionId
  const messages = activeSessionId ? (messagesBySession[activeSessionId] ?? EMPTY_MESSAGES) : EMPTY_MESSAGES
  const sendQuery = useInvestmentStore((state) => state.sendQuery)
  const regenerateMessage = useInvestmentStore((state) => state.regenerateMessage)

  useEffect(() => {
    if (isEmptyClientChat) return
    stackRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [messages, isCurrentSessionPending, isEmptyClientChat])

  const submit = () => {
    const value = query.trim()
    if (!value || isCurrentSessionPending) return
    setQuery('')
    void sendQuery(value).catch((error: unknown) => {
      const detail = error instanceof Error ? error.message : ''
      const backendUnreachable = /failed|fetch|network|502|503|ECONNREFUSED|Load failed/i.test(detail)
      window.alert(
        backendUnreachable
          ? '无法连接后端服务（8099）。请确认后端已启动，并设置 LANGGRAPH_ENV=local 后重启 uvicorn。'
          : detail || '发送失败，请稍后重试。',
      )
    })
  }

  const composer = (
    <Composer
      query={query}
      disabled={isCurrentSessionPending}
      variant={isEmptyClientChat ? 'hero' : 'default'}
      onChange={setQuery}
      onSubmit={submit}
    />
  )

  if (isEmptyClientChat) {
    return (
      <section className="chat-view is-empty">
        <div className="chat-empty-hero">
          <div className="chat-empty-greeting">
            <TideSignalAnimatedLogo />
            <h2 className="chat-empty-title">{marketGreeting}</h2>
          </div>
          <div className="chat-empty-composer-wrap">{composer}</div>
          <div className="chat-empty-suggestions" role="list">
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="chat-empty-chip"
                onClick={() => setQuery(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="chat-view">
      <div className="messages">
        <div className="message-stack">
          {messages.map((rawMessage) => {
            const message = sanitizeMessage(rawMessage)
            const isStreaming = Boolean(message.streaming)
            const showThinking = message.role === 'assistant' && isStreaming && !message.content.trim()
            const visibleBlocks = message.rich_blocks
            const hasAnswerBody = Boolean(message.content.trim()) || visibleBlocks.length > 0
            const showPhaseLabel =
              message.role === 'assistant' && isStreaming && Boolean(message.status_label) && !hasAnswerBody
            const showInlineContent = Boolean(message.content.trim())
            const isPendingId = message.id.startsWith('pending_')
            const showActions =
              message.role === 'assistant' && !isStreaming && hasAnswerBody && !isPendingId
            const isRegeneratingThis =
              isCurrentSessionPending &&
              pendingQuery?.regeneratingAssistantId === message.id
            const actionsDisabled = isCurrentSessionPending

            return (
              <div key={message.id} className={`message ${message.role}`}>
                {message.role === 'assistant' ? (
                  <div className="assistant-block assistant-bubble">
                    {showThinking ? (
                      <div className="thinking-indicator" aria-live="polite">
                        <span className="thinking-label">{message.status_label ?? 'Thinking'}</span>
                        <span className="thinking-dots" aria-hidden="true">
                          <span />
                          <span />
                          <span />
                        </span>
                      </div>
                    ) : showPhaseLabel ? (
                      <div className="assistant-phase" aria-live="polite">
                        {message.status_label}
                      </div>
                    ) : null}
                    {showInlineContent ? (
                      <MarkdownContent
                        content={message.content}
                        streaming={isStreaming}
                        flushPending={Boolean(message.content_complete)}
                        showCursor={isStreaming && !message.content_complete}
                      />
                    ) : null}
                    {visibleBlocks.map((block) => (
                      <RichBlockRenderer key={block.id} block={block} />
                    ))}
                    {showActions ? (
                      <AssistantMessageActions
                        message={message}
                        disabled={actionsDisabled}
                        onRegenerate={() => {
                          if (isRegeneratingThis || actionsDisabled) return
                          void regenerateMessage(message.id).catch(() => {
                            window.alert('重新生成失败，请稍后重试。')
                          })
                        }}
                      />
                    ) : null}
                  </div>
                ) : (
                  <div
                    className={`bubble user-bubble${isCurrentSessionPending && message.id.startsWith('pending_user_') ? ' sending' : ''}`}
                  >
                    {message.content}
                  </div>
                )}
              </div>
            )
          })}
          <div ref={stackRef} />
        </div>
      </div>
      {composer}
    </section>
  )
}
