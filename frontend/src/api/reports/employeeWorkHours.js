import { appendPagination, authFetch } from './http.js'

export async function fetchEmployeeWorkHourFilters() {
  return authFetch('/api/reports/employee-work-hours/filters')
}

export async function fetchEmployeeWorkHoursReport({
  page = 1,
  pageSize = 10,
  dateFrom,
  dateTo,
  department,
  shiftType,
  dimension = 'detail',
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (department) params.set('department', department)
  if (shiftType) params.set('shift_type', shiftType)
  if (dimension) params.set('dimension', dimension)
  return authFetch(`/api/reports/employee-work-hours?${params}`)
}
