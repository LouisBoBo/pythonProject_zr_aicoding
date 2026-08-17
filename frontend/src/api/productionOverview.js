import { clearToken, getToken } from './auth'

export async function fetchProductionOverview() {
  const token = getToken()
  if (!token) {
    throw new Error('未登录')
  }

  const response = await fetch('/api/production/overview', {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearToken()
    }
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || '获取生产概览数据失败')
  }

  return response.json()
}

export async function fetchProductionOverviewDashboard({ period = 'day', line = '全部' } = {}) {
  const token = getToken()
  if (!token) {
    throw new Error('未登录')
  }

  const params = new URLSearchParams({ period, line })
  const response = await fetch(`/api/production/overview-v2?${params}`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearToken()
    }
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || '获取生产概览数据失败')
  }

  return response.json()
}
