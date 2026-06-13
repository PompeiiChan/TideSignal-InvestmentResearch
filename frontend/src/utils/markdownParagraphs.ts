function normalizeTableArtifacts(text: string): string {
  return text.replace(/\|\|/g, '|\n|')
}

function isTableLine(line: string): boolean {
  const trimmed = line.trim()
  return trimmed.startsWith('|') || /\|.+\|/.test(trimmed)
}

function isTableParagraph(paragraph: string): boolean {
  const trimmed = paragraph.trim()
  return trimmed.length > 0 && isTableLine(trimmed)
}

/** Merge backend paragraphs[] into renderable markdown (preserves GFM tables). */
export function paragraphsToMarkdown(paragraphs: string[]): string {
  if (!paragraphs.length) return ''

  const chunks: string[] = []
  let tableLines: string[] = []

  const flushTable = () => {
    if (tableLines.length > 0) {
      chunks.push(tableLines.join('\n'))
      tableLines = []
    }
  }

  for (const raw of paragraphs) {
    const normalized = normalizeTableArtifacts(raw).trim()
    if (!normalized) continue

    if (isTableParagraph(normalized)) {
      const lines = normalized.split('\n').map((line) => line.trim()).filter(Boolean)
      for (const line of lines) {
        if (isTableLine(line)) {
          tableLines.push(line)
        } else {
          flushTable()
          chunks.push(line)
        }
      }
      continue
    }

    flushTable()
    chunks.push(normalized)
  }

  flushTable()
  return chunks.join('\n\n')
}
