import { authFetch } from './http.js'

export async function fetchRepairs({
  page = 1,
  pageSize = 10,
  keyword,
  status,
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (keyword) params.set('keyword', keyword)
  if (status) params.set('status', status)
  return authFetch(`/api/equipment-repairs?${params}`)
}

export async function fetchRepairDetail(id) {
  return authFetch(`/api/equipment-repairs/${id}`)
}

export async function fetchRepairParts(id) {
  return authFetch(`/api/equipment-repairs/${id}/parts`)
}

export async function createRepair(data) {
  return authFetch('/api/equipment-repairs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateRepair(id, data) {
  return authFetch(`/api/equipment-repairs/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function deleteRepair(id) {
  return authFetch(`/api/equipment-repairs/${id}`, { method: 'DELETE' })
}
