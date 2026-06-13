/** Completed lines render as markdown; the last line stays plain until newline or flush. */
export function splitStreamingMarkdown(
  content: string,
  flushPending = false,
): { renderable: string; pending: string } {
  if (!content) return { renderable: '', pending: '' }
  if (flushPending || content.endsWith('\n')) {
    return { renderable: content, pending: '' }
  }

  const lastNewline = content.lastIndexOf('\n')
  if (lastNewline < 0) return { renderable: '', pending: content }

  return {
    renderable: content.slice(0, lastNewline + 1),
    pending: content.slice(lastNewline + 1),
  }
}
