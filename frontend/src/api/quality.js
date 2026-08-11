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

export async function fetchQualityKpi(period = 'day') {
  return authFetch(`/api/quality/kpi?period=${period}`)
}

export async function fetchQualityTrend(granularity = 'day', days = 30) {
  return authFetch(`/api/quality/trend?granularity=${granularity}&days=${days}`)
}

export async function fetchProcessYield() {
  return authFetch('/api/quality/process-yield')
}

export async function fetchDefectDistribution(by = 'type') {
  return authFetch(`/api/quality/defect-distribution?by=${by}`)
}

export async function fetchQualityAnomalies(status = 'open', limit = 20) {
  return authFetch(`/api/quality/anomalies?status=${status}&limit=${limit}`)
}

export async function fetchTopDefects(limit = 10) {
  return authFetch(`/api/quality/top-defects?limit=${limit}`)
}
