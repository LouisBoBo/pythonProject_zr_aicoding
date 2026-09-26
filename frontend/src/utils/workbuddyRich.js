/** WorkBuddy SSE done 载荷：表格 / 图表 / 脚注（与原生 UI 对齐） */

export function normalizeWbTable(raw) {
  if (!Array.isArray(raw)) return []
  return raw
    .map((row) => {
      if (!row || typeof row !== 'object') return null
      const label = row.label ?? row.name ?? row.key ?? ''
      const value = row.value ?? row.count ?? row.val ?? ''
      if (label === '' && value === '') return null
      return {
        label: String(label),
        value: String(value),
        extra: row.extra != null ? String(row.extra) : '',
      }
    })
    .filter(Boolean)
}

export function sumTableCounts(rows) {
  if (!rows?.length) return null
  let sum = 0
  for (const row of rows) {
    const m = String(row.value).match(/(\d+(?:\.\d+)?)/)
    if (!m) return null
    sum += Number(m[1])
  }
  return sum
}

export function guessTableHeaders(rows) {
  const sample = rows.map((r) => r.label).join('')
  if (/线|产线|SMT|DIP|组装|测试/.test(sample)) {
    return ['产线', '在制工单数']
  }
  return ['项目', '数值']
}

export function applyWorkBuddyDonePayload(assistant, evt) {
  if (!assistant || !evt) return
  assistant.wbTable = normalizeWbTable(evt.table)
  const chart = evt.chart
  assistant.wbChart =
    typeof chart === 'string' && chart.startsWith('data:image') ? chart : ''
  assistant.wbNote = evt.note != null ? String(evt.note) : ''
}

export function hasRichPayload(msg) {
  return !!(msg?.wbTable?.length || msg?.wbChart || msg?.wbNote)
}

export function parseRowNumeric(value) {
  const m = String(value ?? '').match(/(\d+(?:\.\d+)?)/)
  return m ? Number(m[1]) : null
}

export function canRenderTableChart(rows) {
  if (!rows?.length) return false
  return rows.every((r) => parseRowNumeric(r.value) != null)
}

const BAR_COLORS = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452']

/** 用表格数据在前端重绘柱状图，避免上游 Matplotlib 中文缺字 */
export function tableToBarChartOption(rows, { title = '' } = {}) {
  const labels = rows.map((r) => r.label)
  const values = rows.map((r) => parseRowNumeric(r.value) ?? 0)
  const colored = values.map((v, i) => ({
    value: v,
    itemStyle: { color: BAR_COLORS[i % BAR_COLORS.length], borderRadius: [4, 4, 0, 0] },
  }))
  return {
    title: title
      ? {
          text: title,
          left: 'center',
          top: 4,
          textStyle: { fontSize: 14, fontWeight: 600, color: '#1f2937' },
        }
      : undefined,
    grid: { left: 44, right: 12, top: title ? 44 : 20, bottom: labels.length > 4 ? 52 : 32 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: {
        interval: 0,
        rotate: labels.length > 4 ? 22 : 0,
        color: '#4b5563',
        fontSize: 12,
      },
      axisLine: { lineStyle: { color: '#e5e7eb' } },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      axisLabel: { color: '#6b7280' },
    },
    series: [
      {
        type: 'bar',
        data: colored,
        barMaxWidth: 52,
        label: { show: true, position: 'top', color: '#374151', fontSize: 12 },
      },
    ],
  }
}

/** 复制用纯文本：正文 + 表格 + 脚注（不含图片） */
export function formatAssistantCopyText(msg) {
  if (!msg) return ''
  const parts = []
  const body = String(msg.text || '').trim()
  if (body) parts.push(body)
  const rows = normalizeWbTable(msg.wbTable)
  if (rows.length) {
    const [h0, h1] = guessTableHeaders(rows)
    const lines = [`${h0}\t${h1}`, ...rows.map((r) => `${r.label}\t${r.value}`)]
    const sum = sumTableCounts(rows)
    if (sum != null) lines.push(`合计\t${sum} 个`)
    parts.push(lines.join('\n'))
  }
  const note = String(msg.wbNote || '').trim()
  if (note) parts.push(note)
  return parts.join('\n\n')
}

export function pickChartTitle(text) {
  const line = String(text || '')
    .replace(/^[\s📊📈]+/, '')
    .split('\n')[0]
    .replace(/\*\*/g, '')
    .trim()
  if (!line) return '数据统计'
  return line.length > 48 ? `${line.slice(0, 48)}…` : line
}
