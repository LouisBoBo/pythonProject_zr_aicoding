import { authFetch } from './http.js'

export function fetchEmployeeWorkHoursList({
  page = 1,
  pageSize = 10,
  employeeNo,
  employeeName,
  department,
  dateFrom,
  dateTo,
  approvalStatus,
} = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  if (employeeNo) params.set('employee_no', employeeNo)
  if (employeeName) params.set('employee_name', employeeName)
  if (department) params.set('department', department)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (approvalStatus) params.set('approval_status', approvalStatus)
  return authFetch(`/api/employee-work-hours?${params.toString()}`)
}
