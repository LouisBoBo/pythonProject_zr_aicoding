import { appendPagination, authFetch } from './http.js'

export async function fetchWipProcesses() {
  return authFetch('/api/reports/wip/processes')
}

export async function fetchWipReport({
  page = 1,
  pageSize = 10,
  status,
  process,
  startDate,
  endDate,
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (status) params.set('status', status)
  if (process) params.set('process', process)
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  return authFetch(`/api/reports/wip?${params}`)
}
