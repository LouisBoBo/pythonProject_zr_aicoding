import { appendPagination, authFetch } from './http.js'

export async function fetchDailyOutputLines() {
  return authFetch('/api/reports/daily-output/lines')
}

export async function fetchDailyOutputReport({
  page = 1,
  pageSize = 10,
  dateFrom,
  dateTo,
  productionLine,
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (productionLine) params.set('production_line', productionLine)
  return authFetch(`/api/reports/daily-output?${params}`)
}
