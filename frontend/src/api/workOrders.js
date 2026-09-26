import { authFetch } from './http.js'

export async function fetchWorkOrders({
  page = 1,
  pageSize = 10,
  status,
  priority,
  productionLine,
  orderNo,
  productName,
  search,
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (status) params.set('status', status)
  if (priority) params.set('priority', priority)
  if (productionLine) params.set('production_line', productionLine)
  if (orderNo) params.set('order_no', orderNo)
  if (productName) params.set('product_name', productName)
  if (search) params.set('search', search)
  return authFetch(`/api/work-orders?${params}`)
}

export async function fetchWorkOrder(id) {
  return authFetch(`/api/work-orders/${id}`)
}

export async function createWorkOrder(data) {
  return authFetch('/api/work-orders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateWorkOrder(id, data) {
  return authFetch(`/api/work-orders/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateWorkOrderStatus(id, status) {
  return authFetch(`/api/work-orders/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
}

export async function deleteWorkOrder(id) {
  return authFetch(`/api/work-orders/${id}`, {
    method: 'DELETE',
  })
}
