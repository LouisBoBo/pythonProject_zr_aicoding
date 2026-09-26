/** 轻量 Markdown 渲染（列表、加粗、段落），无第三方依赖 */

export function normalizeAssistantText(text) {
  return String(text || '')
    .replace(/\\n/g, '\n')
    .replace(/\r\n/g, '\n')
}

export function escapeHtml(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

export function renderMarkdownLite(text) {
  const raw = normalizeAssistantText(text).trim()
  if (!raw) return ''

  const lines = raw.split('\n')
  const out = []
  let inUl = false
  let inOl = false
  let para = []

  function flushPara() {
    if (!para.length) return
    const body = para
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => inlineFormat(line))
      .join('<br>\n')
    if (body) out.push(`<p>${body}</p>`)
    para = []
  }

  function closeLists() {
    if (inUl) {
      out.push('</ul>')
      inUl = false
    }
    if (inOl) {
      out.push('</ol>')
      inOl = false
    }
  }

  function inlineFormat(s) {
    let esc = escapeHtml(s)
    esc = esc.replace(/`([^`]+)`/g, '<code>$1</code>')
    esc = esc.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    return esc
  }

  function isTableRow(trimmed) {
    return trimmed.startsWith('|') && trimmed.includes('|', 1)
  }

  function isTableSeparator(trimmed) {
    if (!isTableRow(trimmed)) return false
    const cells = parseTableCells(trimmed)
    return cells.length > 0 && cells.every((c) => /^:?-{3,}:?$/.test(c))
  }

  function parseTableCells(trimmed) {
    const inner = trimmed.replace(/^\|/, '').replace(/\|\s*$/, '')
    return inner.split('|').map((c) => c.trim())
  }

  function renderTable(tableLines) {
    if (!tableLines.length) return ''
    let bodyStart = 0
    let headerCells = null
    if (tableLines.length >= 2 && isTableSeparator(tableLines[1])) {
      headerCells = parseTableCells(tableLines[0])
      bodyStart = 2
    } else if (tableLines.length >= 1 && !isTableSeparator(tableLines[0])) {
      headerCells = parseTableCells(tableLines[0])
      bodyStart = 1
    } else if (isTableSeparator(tableLines[0])) {
      bodyStart = 1
    }

    const parts = ['<table class="md-table">']
    if (headerCells?.length) {
      parts.push('<thead><tr>')
      for (const cell of headerCells) {
        parts.push(`<th>${inlineFormat(cell)}</th>`)
      }
      parts.push('</tr></thead>')
    }
    parts.push('<tbody>')
    for (let r = bodyStart; r < tableLines.length; r++) {
      if (isTableSeparator(tableLines[r])) continue
      const cells = parseTableCells(tableLines[r])
      if (!cells.length) continue
      parts.push('<tr>')
      for (const cell of cells) {
        parts.push(`<td>${inlineFormat(cell)}</td>`)
      }
      parts.push('</tr>')
    }
    parts.push('</tbody></table>')
    return parts.join('')
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()
    if (!trimmed) {
      flushPara()
      closeLists()
      continue
    }

    if (isTableRow(trimmed)) {
      flushPara()
      closeLists()
      const tableLines = []
      while (i < lines.length) {
        const row = lines[i].trim()
        if (!row) break
        if (!isTableRow(row)) break
        tableLines.push(row)
        i++
      }
      i--
      out.push(renderTable(tableLines))
      continue
    }

    const ul = /^[-*•]\s+(.+)$/.exec(trimmed)
    const ol = /^\d+[.)]\s+(.+)$/.exec(trimmed)
    const h = /^(#{1,3})\s+(.+)$/.exec(trimmed)

    if (h) {
      flushPara()
      closeLists()
      const level = h[1].length
      out.push(`<h${level + 2}>${inlineFormat(h[2])}</h${level + 2}>`)
      continue
    }

    if (ul) {
      flushPara()
      if (inOl) closeLists()
      if (!inUl) {
        out.push('<ul>')
        inUl = true
      }
      out.push(`<li>${inlineFormat(ul[1])}</li>`)
      continue
    }

    if (ol) {
      flushPara()
      if (inUl) closeLists()
      if (!inOl) {
        out.push('<ol>')
        inOl = true
      }
      out.push(`<li>${inlineFormat(ol[1])}</li>`)
      continue
    }

    closeLists()
    para.push(trimmed)
  }

  flushPara()
  closeLists()
  return out.join('')
}
