import { appendPagination, authFetch } from './http.js'

export async function fetchEmployeeWorkHoursFilters() {
  return authFetch('/api/reports/employee-work-hours/filters')
}

export async function fetchEmployeeWorkHoursReport({
  page = 1,
  pageSize = 10,
  dateFrom,
  dateTo,
  employeeNo,
  departmentName,
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (employeeNo) params.set('employee_no', employeeNo)
  if (departmentName) params.set('department_name', departmentName)
  return authFetch(`/api/reports/employee-work-hours?${params}`)
}
