import { authFetch } from './http.js'

/** 分页查询操作审计日志（需 audit.read） */
export function fetchAuditLogs({
  page = 1,
  pageSize = 20,
  username,
  action,
  resource,
} = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  if (username) params.set('username', username)
  if (action) params.set('action', action)
  if (resource) params.set('resource', resource)
  return authFetch(`/api/audit-logs?${params.toString()}`)
}
