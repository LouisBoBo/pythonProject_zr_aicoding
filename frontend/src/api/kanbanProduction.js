import { clearToken, getToken } from './auth'

export async function fetchProductionKanban({ boardCategory = 'production' } = {}) {
  const token = getToken()
  if (!token) {
    throw new Error('未登录')
  }

  const params = new URLSearchParams({ board_category: boardCategory })
  const response = await fetch(`/api/kanban/production?${params}`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearToken()
    }
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || '获取生产看板数据失败')
  }

  return response.json()
}
