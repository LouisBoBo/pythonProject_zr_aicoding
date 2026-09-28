import { appendPagination, authFetch } from './http.js'

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
  projectName,
  shiftType,
  approvalStatus,
  dimension = 'detail',
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (department) params.set('department', department)
  if (employeeNo) params.set('employee_no', employeeNo)
  if (projectName) params.set('project_name', projectName)
  if (shiftType) params.set('shift_type', shiftType)
  if (approvalStatus) params.set('approval_status', approvalStatus)
  if (dimension) params.set('dimension', dimension)
  return authFetch(`/api/reports/employee-work-hours?${params}`)
}
