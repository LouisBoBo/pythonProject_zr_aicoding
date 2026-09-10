import { appendPagination, authFetch } from './http.js'

export async function fetchDailyOutputFilters() {
  return authFetch('/api/reports/daily-output/filters')
}

/** @deprecated 请使用 fetchDailyOutputFilters */
export async function fetchDailyOutputLines() {
  const resp = await fetchDailyOutputFilters()
  return { lines: resp.lines || [] }
}

export async function fetchDailyOutputReport({
  page = 1,
  pageSize = 10,
  dateFrom,
  dateTo,
  productionLine,
  workshop,
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (productionLine) params.set('production_line', productionLine)
  if (workshop) params.set('workshop', workshop)
  return authFetch(`/api/reports/daily-output?${params}`)
}
