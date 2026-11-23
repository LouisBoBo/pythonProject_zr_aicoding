import { authFetch } from './http.js'

function qs(params = {}) {
  const p = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') p.set(k, String(v))
  })
  const s = p.toString()
  return s ? `?${s}` : ''
}

export function fetchIpqcTemplates({ page = 1, pageSize = 20, keyword, processName, status } = {}) {
  return authFetch(
    `/api/quality/ipqc/templates${qs({
      page,
      page_size: pageSize,
      keyword,
      process_name: processName,
      status,
    })}`,
  )
}

export function fetchIpqcTemplate(id) {
  return authFetch(`/api/quality/ipqc/templates/${id}`)
}

export function createIpqcTemplate(body) {
  return authFetch('/api/quality/ipqc/templates', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function updateIpqcTemplate(id, body) {
  return authFetch(`/api/quality/ipqc/templates/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function fetchIpqcTemplateVersions({ templateId, templateCode } = {}) {
  return authFetch(
    `/api/quality/ipqc/template-versions${qs({
      template_id: templateId,
      template_code: templateCode,
    })}`,
  )
}

export function fetchIpqcTestItems({ page = 1, pageSize = 20, keyword, processName, status } = {}) {
  return authFetch(
    `/api/quality/ipqc/test-items${qs({
      page,
      page_size: pageSize,
      keyword,
      process_name: processName,
      status,
    })}`,
  )
}

export function createIpqcTestItem(body) {
  return authFetch('/api/quality/ipqc/test-items', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function updateIpqcTestItem(id, body) {
  return authFetch(`/api/quality/ipqc/test-items/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function createIpqcRecord(body) {
  return authFetch('/api/quality/ipqc/records', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function fetchIpqcRecord(id) {
  return authFetch(`/api/quality/ipqc/records/${id}`)
}

export function updateIpqcRecord(id, body) {
  return authFetch(`/api/quality/ipqc/records/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function generateIpqcRecordItems(id) {
  return authFetch(`/api/quality/ipqc/records/${id}/generate-items`, {
    method: 'POST',
  })
}

export function enrichIpqcData() {
  return authFetch('/api/quality/ipqc/enrich', { method: 'POST' })
}
