import { authFetch } from './http.js'

export async function fetchProductionKanban({ boardCategory = 'production' } = {}) {
  const params = new URLSearchParams({ board_category: boardCategory })
  return authFetch(`/api/kanban/production?${params}`, {}, '获取生产看板数据失败')
}
