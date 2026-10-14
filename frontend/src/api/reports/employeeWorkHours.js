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
  shiftType,
  projectName,
  approvalStatus,
  dimension = 'detail',
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (department) params.set('department', department)
  if (shiftType) params.set('shift_type', shiftType)
  if (projectName) params.set('project_name', projectName)
  if (approvalStatus) params.set('approval_status', approvalStatus)
  if (dimension) params.set('dimension', dimension)
  return authFetch(`/api/reports/employee-work-hours?${params}`)
}

/** 批量通过/驳回待审批工时 */
export async function batchApproveEmployeeWorkHours({ ids, approvalStatus }) {
  return authFetch('/api/reports/employee-work-hours/batch-approval', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ids,
      approval_status: approvalStatus,
    }),
  })
}

/** 导出 Excel（blob） */
export async function exportEmployeeWorkHoursReport(query = {}) {
  const params = new URLSearchParams()
  if (query.dateFrom) params.set('date_from', query.dateFrom)
  if (query.dateTo) params.set('date_to', query.dateTo)
  if (query.department) params.set('department', query.department)
  if (query.shiftType) params.set('shift_type', query.shiftType)
  if (query.projectName) params.set('project_name', query.projectName)
  if (query.approvalStatus) params.set('approval_status', query.approvalStatus)
  if (query.dimension) params.set('dimension', query.dimension)
  return authFetchBlob(`/api/reports/employee-work-hours/export?${params}`)
}
