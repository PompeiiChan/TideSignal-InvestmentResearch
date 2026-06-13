const CITATION_GROUP_RE = /(\[citation:(?:\d+|财务)\])+/g
const SOURCE_META_RE = /（\s*time_period:\s*[^，)]+(?:，\s*来源：[^）]+)?\s*）/g

/** Normalize ### 参考来源 list lines to `[citation:N]标题` and strip technical metadata. */
export function normalizeReferenceSources(content: string): string {
  const heading = '### 参考来源'
  const start = content.indexOf(heading)
  if (start === -1) return content

  const head = content.slice(0, start + heading.length)
  const tail = content.slice(start + heading.length)
  const nextHeading = tail.search(/\n###\s+/)
  const sectionBody = nextHeading === -1 ? tail : tail.slice(0, nextHeading)
  const rest = nextHeading === -1 ? '' : tail.slice(nextHeading)

  const normalizedBody = sectionBody.replace(
    /^(\s*[-*]\s*)(.+)$/gm,
    (_line, bullet: string, rawItem: string) => {
      const citations = rawItem.match(CITATION_GROUP_RE)?.[0] ?? ''
      let title = rawItem.replace(CITATION_GROUP_RE, '').replace(SOURCE_META_RE, '').trim()
      title = title.replace(/：用于.+$/u, '').trim()
      if (/未覆盖|暂未覆盖|工具返回\s*N\/A/i.test(title)) return ''
      if (!title) return citations ? `${bullet}${citations}`.trimEnd() : ''
      if (citations) return `${bullet}${citations}${title}`
      return `${bullet}${title}`
    },
  )

  return `${head}${normalizedBody}${rest}`
}

export function prepareAssistantMarkdown(content: string): string {
  return normalizeReferenceSources(content)
}

export function isCitationHref(href?: string): boolean {
  return typeof href === 'string' && href.startsWith('#cite-')
}
