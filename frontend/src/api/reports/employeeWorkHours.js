import { appendPagination, authFetch } from './http.js'

export async function fetchEmployeeWorkHoursFilters() {
  return authFetch('/api/reports/employee-work-hours/filters')
}

export async function fetchEmployeeWorkHoursReport({
  page = 1,
  pageSize = 10,
  startDate,
  endDate,
  department,
  keyword,
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  if (department) params.set('department', department)
  if (keyword) params.set('keyword', keyword)
  return authFetch(`/api/reports/employee-work-hours?${params}`)
}