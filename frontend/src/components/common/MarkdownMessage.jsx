function MarkdownMessage({ content }) {
  const blocks = parseBlocks(String(content || ''))

  return (
    <div className="space-y-3 text-sm leading-6 text-zinc-200">
      {blocks.map((block, index) => renderBlock(block, index))}
    </div>
  )
}

function parseBlocks(content) {
  const lines = content.replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let paragraph = []
  let list = []
  let table = []

  function flushParagraph() {
    if (paragraph.length) {
      blocks.push({ type: 'paragraph', text: paragraph.join(' ') })
      paragraph = []
    }
  }

  function flushList() {
    if (list.length) {
      blocks.push({ type: 'list', items: list })
      list = []
    }
  }

  function flushTable() {
    if (table.length) {
      blocks.push({ type: 'table', rows: table })
      table = []
    }
  }

  for (const rawLine of lines) {
    const line = rawLine.trim()

    if (!line) {
      flushParagraph()
      flushList()
      flushTable()
      continue
    }

    if (/^-{3,}$/.test(line)) {
      flushParagraph()
      flushList()
      flushTable()
      blocks.push({ type: 'rule' })
      continue
    }

    if (line.startsWith('|') && line.endsWith('|')) {
      flushParagraph()
      flushList()
      table.push(line)
      continue
    }

    flushTable()

    if (line.startsWith('### ')) {
      flushParagraph()
      flushList()
      blocks.push({ type: 'heading', level: 3, text: line.slice(4) })
      continue
    }

    if (line.startsWith('## ')) {
      flushParagraph()
      flushList()
      blocks.push({ type: 'heading', level: 2, text: line.slice(3) })
      continue
    }

    if (line.startsWith('# ')) {
      flushParagraph()
      flushList()
      blocks.push({ type: 'heading', level: 1, text: line.slice(2) })
      continue
    }

    if (line.startsWith('> ')) {
      flushParagraph()
      flushList()
      blocks.push({ type: 'quote', text: line.slice(2) })
      continue
    }

    const listMatch = line.match(/^[-*]\s+(.+)$/) || line.match(/^\d+\.\s+(.+)$/)
    if (listMatch) {
      flushParagraph()
      list.push(listMatch[1])
      continue
    }

    flushList()
    paragraph.push(line)
  }

  flushParagraph()
  flushList()
  flushTable()

  return blocks
}

function renderBlock(block, index) {
  if (block.type === 'heading') {
    const className =
      block.level === 1
        ? 'text-xl font-semibold text-white'
        : block.level === 2
          ? 'text-lg font-semibold text-white'
          : 'text-base font-semibold text-white'

    return (
      <h3 key={index} className={className}>
        {renderInline(block.text)}
      </h3>
    )
  }

  if (block.type === 'list') {
    return (
      <ul key={index} className="list-disc space-y-1 pl-5 text-zinc-200">
        {block.items.map((item, itemIndex) => (
          <li key={itemIndex}>{renderInline(item)}</li>
        ))}
      </ul>
    )
  }

  if (block.type === 'quote') {
    return (
      <blockquote key={index} className="border-l-2 border-cyan-400/50 pl-3 text-zinc-300">
        {renderInline(block.text)}
      </blockquote>
    )
  }

  if (block.type === 'table') {
    return <MarkdownTable key={index} rows={block.rows} />
  }

  if (block.type === 'rule') {
    return <hr key={index} className="border-zinc-800" />
  }

  return (
    <p key={index} className="text-zinc-200">
      {renderInline(block.text)}
    </p>
  )
}

function MarkdownTable({ rows }) {
  const parsedRows = rows
    .map((row) =>
      row
        .split('|')
        .slice(1, -1)
        .map((cell) => cell.trim()),
    )
    .filter((row) => !row.every((cell) => /^:?-{2,}:?$/.test(cell)))

  if (!parsedRows.length) {
    return null
  }

  const [header, ...body] = parsedRows

  return (
    <div className="overflow-x-auto rounded-md border border-zinc-800">
      <table className="min-w-full border-collapse text-left text-sm">
        <thead className="bg-zinc-950 text-zinc-300">
          <tr>
            {header.map((cell, index) => (
              <th key={index} className="border-b border-zinc-800 px-3 py-2 font-semibold">
                {renderInline(cell)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, rowIndex) => (
            <tr key={rowIndex} className="border-t border-zinc-800/70">
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className="px-3 py-2 text-zinc-300">
                  {renderInline(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function renderInline(text) {
  const parts = String(text).split(/(\*\*[^*]+\*\*|`[^`]+`)/g)

  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={index} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      )
    }

    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={index} className="rounded bg-zinc-950 px-1.5 py-0.5 text-cyan-200">
          {part.slice(1, -1)}
        </code>
      )
    }

    return part
  })
}

export default MarkdownMessage
