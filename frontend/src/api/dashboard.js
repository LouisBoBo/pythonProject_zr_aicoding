import { clearToken, getToken } from './auth'

export async function fetchDashboard() {
  const token = getToken()
  if (!token) {
    throw new Error('未登录')
  }

  const response = await fetch('/api/dashboard', {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearToken()
    }
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || '获取仪表盘数据失败')
  }

  return response.json()
}
