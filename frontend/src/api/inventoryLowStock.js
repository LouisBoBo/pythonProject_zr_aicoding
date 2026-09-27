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
