import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import { splitStreamingMarkdown } from '../utils/streamingMarkdown'
import { isCitationHref, prepareAssistantMarkdown } from '../utils/citationMarkdown'
import { remarkCitations } from '../utils/remarkCitations'

const markdownComponents: Components = {
  a: ({ href, children }) => {
    if (isCitationHref(href)) {
      return <span className="citation-tag">{children}</span>
    }
    return (
      <a href={href} target="_blank" rel="noreferrer">
        {children}
      </a>
    )
  },
  table: ({ children }) => (
    <div className="markdown-table-wrap">
      <table className="data-table">{children}</table>
    </div>
  ),
  blockquote: ({ children }) => <blockquote className="judgment-highlight">{children}</blockquote>,
}

type MarkdownContentProps = {
  content: string
  streaming?: boolean
  flushPending?: boolean
  showCursor?: boolean
}

export function MarkdownContent({
  content,
  streaming = false,
  flushPending = false,
  showCursor = false,
}: MarkdownContentProps) {
  const trimmed = content.trim()
  if (!trimmed) return null

  const renderMarkdown = (markdown: string) => (
    <ReactMarkdown remarkPlugins={[remarkGfm, remarkCitations]} components={markdownComponents}>
      {markdown}
    </ReactMarkdown>
  )

  if (!streaming) {
    return <div className="markdown-body assistant-text">{renderMarkdown(prepareAssistantMarkdown(trimmed))}</div>
  }

  const { renderable, pending } = splitStreamingMarkdown(content, flushPending)
  const preparedRenderable = renderable.trim() ? prepareAssistantMarkdown(renderable.trim()) : ''

  return (
    <div className="markdown-body assistant-text streaming">
      {preparedRenderable ? renderMarkdown(preparedRenderable) : null}
      {pending ? (
        <span className="streaming-pending">
          {pending}
          {showCursor ? <span className="stream-cursor" aria-hidden="true" /> : null}
        </span>
      ) : showCursor ? (
        <span className="stream-cursor" aria-hidden="true" />
      ) : null}
    </div>
  )
}
