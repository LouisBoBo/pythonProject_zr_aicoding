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

export async function fetchWipReport({
  page = 1,
  pageSize = 10,
  status,
  process,
  startDate,
  endDate,
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (status) params.set('status', status)
  if (process) params.set('process', process)
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  return authFetch(`/api/reports/wip?${params}`)
}

export async function fetchWipProcesses() {
  return authFetch('/api/reports/wip/processes')
}
