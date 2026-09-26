import { authFetch } from './http.js'

export async function fetchDashboard() {
  return authFetch('/api/dashboard', {}, '获取仪表盘数据失败')
}
