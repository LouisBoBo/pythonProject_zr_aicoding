import { authFetch } from './http.js'

export async function fetchProductionOverview() {
  return authFetch('/api/production/overview', {}, '获取生产概览数据失败')
}

export async function fetchProductionOverviewDashboard({ period = 'day', line = '全部' } = {}) {
  const params = new URLSearchParams({ period, line })
  return authFetch(`/api/production/overview-v2?${params}`, {}, '获取生产概览数据失败')
}
