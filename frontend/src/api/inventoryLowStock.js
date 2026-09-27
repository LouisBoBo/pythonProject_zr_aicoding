import { authFetch } from './http.js'

/** 低库存预警列表 */
export function fetchInventoryLowStock({ page = 1, size = 10, warehouseName, keyword } = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('size', String(size))
  if (warehouseName) params.set('warehouse_name', warehouseName)
  if (keyword) params.set('keyword', keyword)
  return authFetch(`/api/inventory-low-stock?${params.toString()}`)
}

/** 登记发货数量与时间（校验剩余可发，发满关单） */
export function registerLowStockShipment(stockId, { salesOrderId, shipQty, shippedAt } = {}) {
  const body = {
    sales_order_id: salesOrderId,
    ship_qty: shipQty,
  }
  if (shippedAt) body.shipped_at = shippedAt
  return authFetch(`/api/inventory-low-stock/${stockId}/register-shipment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}
