import { authFetch } from './http.js'

export async function fetchComprehensiveKanban() {
  return authFetch('/api/kanban/general', {}, '获取综合看板数据失败')
}
