import { authFetch } from './http.js'

/** 与后端 GET /api/equipment-repairs 的 page_size 上限 le=100 一致 */
export const REPAIR_LIST_MAX_PAGE_SIZE = 100
export const REPAIR_LIST_DEFAULT_PAGE_SIZE = 10

function normalizeRepairListPageSize(pageSize) {
  const n = Number(pageSize)
  if (!Number.isFinite(n)) return REPAIR_LIST_DEFAULT_PAGE_SIZE
  return Math.min(REPAIR_LIST_MAX_PAGE_SIZE, Math.max(1, Math.trunc(n)))
}

export async function fetchRepairs({
  page = 1,
  pageSize = REPAIR_LIST_DEFAULT_PAGE_SIZE,
  keyword,
  status,
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(normalizeRepairListPageSize(pageSize)),
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
