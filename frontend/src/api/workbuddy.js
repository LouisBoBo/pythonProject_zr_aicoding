import { clearToken, getToken } from './auth'

async function authFetch(url, options = {}) {
  const token = getToken()
  if (!token) throw new Error('未登录')
  const response = await fetch(url, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })
  if (response.status === 204) return null
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) clearToken()
    const detail = data.detail
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail || data) || '请求失败')
  }
  return data
}

export function fetchWorkBuddyMeta() {
  return authFetch('/api/workbuddy/meta')
}

function parseSseLine(line, onEvent) {
  if (!line.startsWith('data:')) return
  const raw = line.slice(5).trim()
  if (!raw) return
  try {
    return onEvent(JSON.parse(raw))
  } catch {
    return onEvent({ type: 'raw', message: raw })
  }
}

/** 消费 WorkBuddy SSE；支持 async onEvent，按行即时解析 */
export async function consumeChatStream(message, onEvent, signal) {
  const token = getToken()
  if (!token) throw new Error('未登录')
  const res = await fetch('/api/workbuddy/chat/stream', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache',
    },
    body: JSON.stringify({ message }),
    signal,
  })
  if (!res.ok || !res.body) {
    const t = await res.text().catch(() => '')
    throw new Error(t || `SSE HTTP ${res.status}`)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buf = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let nl = buf.indexOf('\n')
    while (nl >= 0) {
      const line = buf.slice(0, nl).replace(/\r$/, '')
      buf = buf.slice(nl + 1)
      parseSseLine(line, onEvent)
      nl = buf.indexOf('\n')
    }
  }
  const tail = buf.trim()
  if (tail) parseSseLine(tail, onEvent)
}
