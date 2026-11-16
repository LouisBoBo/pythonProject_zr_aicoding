import { appendPagination, authFetch, authFetchBlob } from './http.js'

export async function fetchEmployeeWorkHourFilters() {
  return authFetch('/api/reports/employee-work-hours/filters')
}

export async function fetchEmployeeWorkHoursReport({
  page = 1,
  pageSize = 10,
  dateFrom,
  dateTo,
  department,
  employeeNo,
  dimension = 'employee_date',
  sortBy = 'work_date',
  sortOrder = 'desc',
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (department) params.set('department', department)
  if (employeeNo) params.set('employee_no', employeeNo)
  if (dimension) params.set('dimension', dimension)
  if (sortBy) params.set('sort_by', sortBy)
  if (sortOrder) params.set('sort_order', sortOrder)
  return authFetch(`/api/reports/employee-work-hours?${params}`)
}

export async function exportEmployeeWorkHoursReport({
  dateFrom,
  dateTo,
  department,
  employeeNo,
  sortBy = 'work_date',
  sortOrder = 'desc',
} = {}) {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (department) params.set('department', department)
  if (employeeNo) params.set('employee_no', employeeNo)
  if (sortBy) params.set('sort_by', sortBy)
  if (sortOrder) params.set('sort_order', sortOrder)
  return authFetchBlob(`/api/reports/employee-work-hours/export?${params}`)
}
