/**
 * 对比：直连 WorkBuddy API vs ERP 8009 代理
 * 指标：首字节、首条 reply、reply 事件数、总耗时、代理额外延迟
 */
const ERP = 'http://127.0.0.1:8009'
const WB_CANDIDATES = ['http://127.0.0.1:18000', 'http://127.0.0.1:8000']

async function loginErp() {
  const res = await fetch(`${ERP}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: 'admin',
      password: 'admin123',
      enterprise_code: '测试企业',
    }),
  })
  const data = await res.json()
  if (!data.access_token) throw new Error('ERP login failed')
  return data.access_token
}

async function probeWbBase() {
  for (const base of WB_CANDIDATES) {
    try {
      const res = await fetch(`${base}/api/health`, { signal: AbortSignal.timeout(3000) })
      if (res.ok) return base
    } catch {
      /* next */
    }
  }
  return null
}

async function streamMetrics(label, url, init) {
  const t0 = performance.now()
  let firstByte = null
  let firstReply = null
  let replyEvents = 0
  let replyChars = 0
  let doneAt = null
  let doneLen = 0

  const res = await fetch(url, init)
  if (!res.ok || !res.body) {
    throw new Error(`${label} HTTP ${res.status}`)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    if (firstByte == null) firstByte = performance.now() - t0
    buf += decoder.decode(value, { stream: true })
    let nl = buf.indexOf('\n')
    while (nl >= 0) {
      const line = buf.slice(0, nl).replace(/\r$/, '')
      buf = buf.slice(nl + 1)
      if (line.startsWith('data:')) {
        try {
          const evt = JSON.parse(line.slice(5).trim())
          if (evt.type === 'reply') {
            replyEvents += 1
            const d = evt.delta || evt.text || ''
            replyChars += d.length
            if (firstReply == null) firstReply = performance.now() - t0
          }
          if (evt.type === 'done') {
            doneAt = performance.now() - t0
            doneLen = (evt.reply || '').length
          }
        } catch {
          /* ignore */
        }
      }
      nl = buf.indexOf('\n')
    }
  }
  if (doneAt == null) doneAt = performance.now() - t0
  return {
    label,
    firstByteMs: firstByte,
    firstReplyMs: firstReply,
    replyEvents,
    replyChars,
    doneMs: doneAt,
    doneLen,
  }
}

async function main() {
  const msg = process.argv[2] || 'PCB有哪些工序'
  const token = await loginErp()
  const wb = await probeWbBase()
  const out = { message: msg, wbBase: wb }

  out.erp = await streamMetrics(`${ERP} proxy`, `${ERP}/api/workbuddy/chat/stream`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message: msg }),
  })

  if (wb) {
    out.wbDirect = await streamMetrics(`${wb} direct`, `${wb}/api/chat/stream`, {
      method: 'POST',
      headers: {
        Accept: 'text/event-stream',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: msg }),
    })
    if (out.erp.firstReplyMs != null && out.wbDirect.firstReplyMs != null) {
      out.proxyReplyOverheadMs = out.erp.firstReplyMs - out.wbDirect.firstReplyMs
      out.proxyDoneOverheadMs = out.erp.doneMs - out.wbDirect.doneMs
    }
  }

  console.log(JSON.stringify(out, null, 2))
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
