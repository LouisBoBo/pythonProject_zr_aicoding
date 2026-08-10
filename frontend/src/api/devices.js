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

export async function fetchDevices({ page = 1, pageSize = 50, search, deviceTypeId, status } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (search) params.set('search', search)
  if (deviceTypeId) params.set('device_type_id', String(deviceTypeId))
  if (status) params.set('status', status)
  return authFetch(`/api/devices?${params}`)
}
