import React, { useMemo } from 'react'

// Lightweight markdown renderer without adding new deps.
// Supports: bold/italic, inline code, fenced code blocks, and basic lists/line breaks.

type Token = { type: 'text' | 'code'; value: string; lang?: string }

function escapeHtml(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '<').replace(/>/g, '>')
}

function parseFencedCodeBlocks(input: string): Token[] {
  // Splits on ```lang\n...\n```
  const tokens: Token[] = []
  const re = /```(\w+)?\n([\s\S]*?)\n```/g
  let lastIndex = 0
  let m: RegExpExecArray | null

  while ((m = re.exec(input))) {
    const start = m.index
    const lang = (m[1] || '').trim() || undefined
    const code = m[2] ?? ''

    if (start > lastIndex) {
      tokens.push({ type: 'text', value: input.slice(lastIndex, start) })
    }

    tokens.push({ type: 'code', value: code, lang })

    lastIndex = start + m[0].length
  }

  if (lastIndex < input.length) {
    tokens.push({ type: 'text', value: input.slice(lastIndex) })
  }

  return tokens
}

function renderInline(text: string) {
  // Very small inline markdown parser
  const parts: React.ReactNode[] = []

  // Handle inline code `...`
  const re = /(`[^`]+`)/g
  const chunks = text.split(re).filter(Boolean)

  for (const chunk of chunks) {
    if (chunk.startsWith('`') && chunk.endsWith('`')) {
      parts.push(
        <code key={parts.length} className="font-mono text-[0.95em] bg-gray-100 px-1 py-0.5 rounded">
          {chunk.slice(1, -1)}
        </code>,
      )
      continue
    }

    // Bold **...**
    // Italic *...*
    // We do this with a simple regex loop.
    let s = chunk

    // Bold
    const boldRe = /\*\*([^*]+)\*\*/g
    const boldChunks = s.split(boldRe)
    if (boldChunks.length > 1) {
      // Rebuild with placeholders for bold groups
      for (let i = 0; i < boldChunks.length; i++) {
        const segment = boldChunks[i]
        if (segment === undefined || segment === '') continue
        // Odd indices are capture groups
        if (i % 2 === 1) {
          parts.push(
            <strong key={parts.length} className="font-semibold">
              {segment}
            </strong>,
          )
        } else {
          // Now italic inside the normal segment
          const italicRe = /\*([^*]+)\*/g
          const italicChunks = segment.split(italicRe)
          for (let j = 0; j < italicChunks.length; j++) {
            const seg2 = italicChunks[j]
            if (seg2 === undefined || seg2 === '') continue
            if (j % 2 === 1) {
              parts.push(
                <em key={parts.length} className="italic">
                  {seg2}
                </em>,
              )
            } else {
              parts.push(<React.Fragment key={parts.length}>{seg2}</React.Fragment>)
            }
          }
        }
      }
    } else {
      // Italic only
      const italicRe = /\*([^*]+)\*/g
      const italicChunks = s.split(italicRe)
      for (let j = 0; j < italicChunks.length; j++) {
        const seg2 = italicChunks[j]
        if (seg2 === undefined || seg2 === '') continue
        if (j % 2 === 1) {
          parts.push(
            <em key={parts.length} className="italic">
              {seg2}
            </em>,
          )
        } else {
          parts.push(<React.Fragment key={parts.length}>{seg2}</React.Fragment>)
        }
      }
    }
  }

  return parts
}

export const Markdown: React.FC<{ content: string }> = ({ content }) => {
  const blocks = useMemo(() => parseFencedCodeBlocks(content || ''), [content])

  return (
    <div className="markdown-body space-y-2">
      {blocks.map((b, idx) => {
        if (b.type === 'code') {
          return (
            <pre key={idx} className="bg-gray-900 text-gray-100 rounded-lg p-3 overflow-x-auto">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs opacity-70 font-mono">{b.lang ? b.lang : 'code'}</span>
              </div>
              <code className="font-mono text-sm">{b.value}</code>
            </pre>
          )
        }

        // Text block: handle lists and line breaks.
        const lines = b.value.split('\n')
        return (
          <div key={idx} className="text-sm leading-relaxed">
            {lines.map((line, li) => {
              const trimmed = line.trim()
              if (/^[-*]\s+/.test(trimmed)) {
                const item = trimmed.replace(/^[-*]\s+/, '')
                return (
                  <div key={li} className="flex gap-2">
                    <span className="mt-0.5 text-gray-400">•</span>
                    <div>{renderInline(item)}</div>
                  </div>
                )
              }

              // Blank line -> spacing
              if (trimmed.length === 0) {
                return <div key={li} className="h-2" />
              }

              return (
                <div key={li}>
                  {renderInline(line)}
                </div>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}

