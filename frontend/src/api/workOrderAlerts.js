import { authFetch } from './http.js'

/** 工单逾期预警列表 */
export function fetchWorkOrderAlerts({ page = 1, size = 10, productionLine, keyword } = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('size', String(size))
  if (productionLine) params.set('production_line', productionLine)
  if (keyword) params.set('keyword', keyword)
  return authFetch(`/api/work-order-alerts?${params.toString()}`)
}
