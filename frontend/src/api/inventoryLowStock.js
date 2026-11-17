import { authFetch } from './http.js'

export function fetchInventoryLowStockList({
  page = 1,
  pageSize = 10,
  materialCode,
  materialName,
  warehouseName,
} = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  if (materialCode) params.set('material_code', materialCode)
  if (materialName) params.set('material_name', materialName)
  if (warehouseName) params.set('warehouse_name', warehouseName)
  return authFetch(`/api/inventory-low-stock?${params.toString()}`)
}
