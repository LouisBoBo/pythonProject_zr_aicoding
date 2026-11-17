/** 验证 SSE：status 先于 reply 到达（经 Vite 5175 代理） */
import { createTextReveal } from '../src/utils/streamReveal.js'
import { normalizeAssistantText } from '../src/utils/markdownLite.js'

async function login() {
  const res = await fetch('http://127.0.0.1:5175/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: 'admin',
      password: 'admin123',
      enterprise_code: '测试企业',
    }),
  })
  const data = await res.json()
  return data.access_token
}

async function main() {
  const token = await login()
  const t0 = performance.now()
  let statusAt = null
  let firstTextAt = null
  let steps = 0

  const streamer = createTextReveal(() => {
    steps += 1
    if (!firstTextAt) firstTextAt = performance.now() - t0
  })

  const res = await fetch('http://127.0.0.1:5175/api/workbuddy/chat/stream', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message: '有什么功能' }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let nl = buf.indexOf('\n')
    while (nl >= 0) {
      const line = buf.slice(0, nl).replace(/\r$/, '')
      buf = buf.slice(nl + 1)
      if (line.startsWith('data:')) {
        const evt = JSON.parse(line.slice(5).trim())
        if (evt.type === 'status' && statusAt == null) statusAt = performance.now() - t0
        if (evt.type === 'reply') {
          const d = normalizeAssistantText(evt.delta || '')
          if (d) await streamer.enqueue(d)
        }
      }
      nl = buf.indexOf('\n')
    }
  }
  await streamer.finished()

  const ok =
    statusAt != null &&
    statusAt < 1500 &&
    firstTextAt != null &&
    firstTextAt > statusAt &&
    steps >= 8
  console.log(JSON.stringify({ ok, statusAtMs: statusAt, firstTextAtMs: firstTextAt, steps }, null, 2))
  process.exit(ok ? 0 : 1)
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
