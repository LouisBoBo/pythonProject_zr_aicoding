/**
 * 模拟前端 SSE 消费 + 分步输出，验证无重复且有多段展示更新
 */
import { createTextReveal, takeStreamIncrement } from '../src/utils/streamReveal.js'
import { normalizeAssistantText } from '../src/utils/markdownLite.js'

function parseSseLines(raw, onEvent) {
  let buf = raw
  let nl = buf.indexOf('\n')
  while (nl >= 0) {
    const line = buf.slice(0, nl).replace(/\r$/, '')
    buf = buf.slice(nl + 1)
    if (line.startsWith('data:')) {
      const payload = line.slice(5).trim()
      if (payload) onEvent(JSON.parse(payload))
    }
    nl = buf.indexOf('\n')
  }
}

async function fetchStream(message, token) {
  const res = await fetch('http://127.0.0.1:8009/api/workbuddy/chat/stream', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let raw = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    raw += decoder.decode(value, { stream: true })
  }
  return raw
}

async function simulateUi(raw) {
  let text = ''
  const updates = []
  const streamer = createTextReveal((chunk) => {
    text += chunk
    updates.push(text.length)
  })

  let serverReply = ''
  const appendFromServer = (chunk) => {
    const { accum, increment } = takeStreamIncrement(serverReply, chunk)
    serverReply = accum
    if (increment) streamer.enqueue(increment)
  }
  const appendDoneTail = (fullText) => {
    appendFromServer(fullText)
  }

  parseSseLines(raw, (evt) => {
    if (evt.type === 'reply') appendFromServer(evt.delta || evt.text || '')
    if (evt.type === 'done') appendDoneTail(evt.reply)
  })

  await streamer.finished()
  return { text, updates }
}

async function login() {
  const res = await fetch('http://127.0.0.1:8009/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: 'admin',
      password: 'admin123',
      enterprise_code: '测试企业',
    }),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(JSON.stringify(data))
  return data.access_token
}

const token = await login()
const raw = await fetchStream('有什么功能', token)
const firstPass = await simulateUi(raw)
const finalText = firstPass.text
const uniqueUpdates = new Set(firstPass.updates).size

// duplicate: if first 40 chars appear twice consecutively at start
const head = finalText.slice(0, 40)
const duplicated = head.length >= 10 && finalText.indexOf(head, 1) === head.length

console.log(
  JSON.stringify(
    {
      ok: !duplicated && uniqueUpdates >= 8 && finalText.length > 20,
      textLen: finalText.length,
      uiUpdateSteps: uniqueUpdates,
      duplicated,
      preview: finalText.slice(0, 80),
    },
    null,
    2,
  ),
)

process.exit(!duplicated && uniqueUpdates >= 8 && finalText.length > 20 ? 0 : 1)
