import { clearToken, getToken } from './auth'

export async function fetchComprehensiveKanban() {
  const token = getToken()
  if (!token) {
    throw new Error('未登录')
  }

  const response = await fetch('/api/kanban/general', {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearToken()
    }
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || '获取综合看板数据失败')
  }

  return response.json()
}
