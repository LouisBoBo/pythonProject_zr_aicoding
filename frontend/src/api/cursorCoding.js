import { getToken } from './auth'
import { authFetch } from './http.js'

const jsonPost = (url, body) =>
  authFetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

export function fetchCursorMeta() {
  return authFetch('/api/cursor-coding/meta')
}

export function prepareProbe() {
  return jsonPost('/api/cursor-coding/prepare-probe', {})
}

export function listLocalRuns() {
  return authFetch('/api/cursor-coding/runs')
}

export function getLocalRun(jobId) {
  return authFetch(`/api/cursor-coding/runs/${encodeURIComponent(jobId)}`)
}

export function confirmCursorJob(body) {
  return jsonPost('/api/cursor-coding/confirm', body)
}

export function fetchJobDialog(jobId) {
  return authFetch(`/api/cursor-coding/jobs/${encodeURIComponent(jobId)}/dialog`)
}

export function listUpstreamJobs() {
  return authFetch('/api/cursor-coding/jobs')
}

export function steerJob(jobId, message) {
  return jsonPost(`/api/cursor-coding/jobs/${encodeURIComponent(jobId)}/steer`, { message })
}

export function applyJob(jobId, accept) {
  return jsonPost(`/api/cursor-coding/jobs/${encodeURIComponent(jobId)}/apply`, { accept })
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
