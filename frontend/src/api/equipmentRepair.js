import { clearToken, getToken } from './auth'

async function authFetch(url, options = {}) {
  const token = getToken()
  if (!token) {
    throw new Error('未登录')
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  })

  if (response.status === 204) {
    return null
  }

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearToken()
    }
    const error = await response.json().catch(() => ({}))
    const detail = error.detail
    const message = typeof detail === 'string' ? detail : '请求失败'
    throw new Error(message)
  }

  return response.json()
}

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
