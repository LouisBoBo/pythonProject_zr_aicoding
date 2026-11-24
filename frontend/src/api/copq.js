import { authFetch } from './http.js'

/** 客户主数据 */
export async function fetchCustomers(keyword) {
  const params = new URLSearchParams()
  if (keyword) params.set('keyword', keyword)
  const q = params.toString()
  return authFetch(`/api/quality/customers${q ? `?${q}` : ''}`)
}

/** 客诉台账列表 */
export async function fetchComplaints({
  page = 1,
  pageSize = 20,
  customerCode,
  status,
  dateFrom,
  dateTo,
} = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  if (customerCode) params.set('customer_code', customerCode)
  if (status) params.set('status', status)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return authFetch(`/api/quality/complaints?${params.toString()}`)
}

/** 新建客诉 */
export async function createComplaint(body) {
  return authFetch('/api/quality/complaints', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

/** COPQ 金额汇总 */
export async function fetchCopqSummary({ dateFrom, dateTo } = {}) {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  const q = params.toString()
  return authFetch(`/api/quality/copq-summary${q ? `?${q}` : ''}`)
}
