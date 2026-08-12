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
    throw new Error(error.detail || '请求失败')
  }

  return response.json()
}

export function fetchDeviceStatusSummary() {
  return authFetch('/api/device/status/summary')
}

export function fetchDeviceOEE() {
  return authFetch('/api/device/oee')
}

export function fetchDeviceDashboardList({ page = 1, pageSize = 20, status = '' } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (status && status !== '全部') params.set('status', status)
  return authFetch(`/api/device/list?${params}`)
}

export function fetchDeviceUtilization(period = 'day') {
  return authFetch(`/api/device/utilization?period=${period}`)
}

export function fetchDeviceAlarmsTrend() {
  return authFetch('/api/device/alarms/trend')
}

export function fetchDeviceOutput() {
  return authFetch('/api/device/output')
}
