import { authFetch } from './http.js'

export function fetchSalesOrders({ page = 1, size = 10, keyword, status } = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('size', String(size))
  if (keyword) params.set('keyword', keyword)
  if (status) params.set('status', status)
  return authFetch(`/api/sales-orders?${params.toString()}`)
}

export function createSalesOrder(body) {
  return authFetch('/api/sales-orders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function fetchOrderShipments(orderId) {
  return authFetch(`/api/sales-orders/${orderId}/shipments`)
}

/** 登记发货数量与时间（校验剩余可发，发满关单） */
export function registerOrderShipment(orderId, { shipQty, shippedAt } = {}) {
  const body = { ship_qty: shipQty }
  if (shippedAt) body.shipped_at = shippedAt
  return authFetch(`/api/sales-orders/${orderId}/register-shipment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}
