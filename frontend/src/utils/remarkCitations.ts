import type { Link, PhrasingContent, Root } from 'mdast'
import type { Plugin } from 'unified'
import { visit } from 'unist-util-visit'

const CITATION_INLINE_RE = /\[citation:(\d+|财务)\]/g

/** Turn `[citation:N]` into non-clickable inline `[N]` spans via mdast (no markdown links). */
export const remarkCitations: Plugin<[], Root> = () => (tree) => {
  visit(tree, 'text', (node, index, parent) => {
    if (index === undefined || !parent) return
    const value = node.value
    if (!value.includes('[citation:')) return

    const next: PhrasingContent[] = []
    let last = 0
    for (const match of value.matchAll(CITATION_INLINE_RE)) {
      const start = match.index ?? 0
      if (start > last) {
        next.push({ type: 'text', value: value.slice(last, start) })
      }
      const id = match[1]
      const label = id === '财务' ? '财务' : id
      next.push({
        type: 'link',
        url: `#cite-${id}`,
        children: [{ type: 'text', value: `[${label}]` }],
      } as Link)
      last = start + match[0].length
    }
    if (last < value.length) {
      next.push({ type: 'text', value: value.slice(last) })
    }
    if (next.length === 0) return
    parent.children.splice(index, 1, ...next)
  })
}
