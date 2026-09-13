import { appendPagination, authFetch, authFetchBlob } from './http.js'

export async function fetchEmployeeWorkHourFilters() {
  return authFetch('/api/reports/employee-work-hours/filters')
}

export async function fetchEmployeeWorkHourReport({
  page = 1,
  pageSize = 10,
  dateFrom,
  dateTo,
  department,
  employeeNo,
  dimension = 'employee',
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (department) params.set('department', department)
  if (employeeNo) params.set('employee_no', employeeNo)
  if (dimension) params.set('dimension', dimension)
  return authFetch(`/api/reports/employee-work-hours?${params}`)
}

export async function exportEmployeeWorkHourReport({
  dateFrom,
  dateTo,
  department,
  employeeNo,
  dimension = 'employee',
} = {}) {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (department) params.set('department', department)
  if (employeeNo) params.set('employee_no', employeeNo)
  if (dimension) params.set('dimension', dimension)
  return authFetchBlob(`/api/reports/employee-work-hours/export?${params}`)
}
