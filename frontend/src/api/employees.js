import { authFetch } from './http.js'

export function fetchEmployeeList({
  page = 1,
  pageSize = 10,
  employeeNo,
  employeeName,
  departmentName,
} = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  if (employeeNo) params.set('employee_no', employeeNo)
  if (employeeName) params.set('employee_name', employeeName)
  if (departmentName) params.set('department_name', departmentName)
  return authFetch(`/api/employees?${params.toString()}`)
}
