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

export function fetchCursorMeta() {
  return authFetch('/api/cursor-coding/meta')
}

export function prepareProbe() {
  return authFetch('/api/cursor-coding/prepare-probe', { method: 'POST', body: '{}' })
}

export function listLocalRuns() {
  return authFetch('/api/cursor-coding/runs')
}

export function getLocalRun(jobId) {
  return authFetch(`/api/cursor-coding/runs/${encodeURIComponent(jobId)}`)
}

export function confirmCursorJob(body) {
  return authFetch('/api/cursor-coding/confirm', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function fetchJobDialog(jobId) {
  return authFetch(`/api/cursor-coding/jobs/${encodeURIComponent(jobId)}/dialog`)
}

export function listUpstreamJobs() {
  return authFetch('/api/cursor-coding/jobs')
}

export function steerJob(jobId, message) {
  return authFetch(`/api/cursor-coding/jobs/${encodeURIComponent(jobId)}/steer`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

export function applyJob(jobId, accept) {
  return authFetch(`/api/cursor-coding/jobs/${encodeURIComponent(jobId)}/apply`, {
    method: 'POST',
    body: JSON.stringify({ accept }),
  })
}

/** 带 JWT 消费 SSE（EventSource 无法自定义头） */
export async function consumeJobStream(jobId, onEvent, signal) {
  const token = getToken()
  if (!token) throw new Error('未登录')
  const res = await fetch(`/api/cursor-coding/jobs/${encodeURIComponent(jobId)}/stream`, {
    headers: { Authorization: `Bearer ${token}`, Accept: 'text/event-stream' },
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
    const chunks = buf.split('\n\n')
    buf = chunks.pop() || ''
    for (const block of chunks) {
      const lines = block.split('\n')
      for (const line of lines) {
        if (!line.startsWith('data:')) continue
        const raw = line.slice(5).trim()
        if (!raw) continue
        try {
          onEvent(JSON.parse(raw))
        } catch {
          onEvent({ type: 'raw', message: raw })
        }
      }
    }
  }
}
