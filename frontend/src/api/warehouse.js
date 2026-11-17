import { authFetch } from './http.js'

export function fetchWarehouseDashboard() {
  return authFetch('/api/warehouse/dashboard')
}

export function fetchInventoryStockList({
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
  return authFetch(`/api/warehouse/inventory-stock?${params.toString()}`)
}

export function fetchWarehouseOptions() {
  return authFetch('/api/warehouse/warehouses')
}

export function fetchMaterialOptions() {
  return authFetch('/api/warehouse/materials')
}

export function fetchLocationOptions({ warehouseId } = {}) {
  const params = new URLSearchParams()
  if (warehouseId) params.set('warehouse_id', String(warehouseId))
  const qs = params.toString()
  return authFetch(`/api/warehouse/locations${qs ? `?${qs}` : ''}`)
}

export function fetchMaterialInboundList({
  page = 1,
  pageSize = 10,
  inboundNo,
  materialCode,
  materialName,
  status,
  dateFrom,
  dateTo,
} = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  if (inboundNo) params.set('inbound_no', inboundNo)
  if (materialCode) params.set('material_code', materialCode)
  if (materialName) params.set('material_name', materialName)
  if (status) params.set('status', status)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return authFetch(`/api/warehouse/material-inbound?${params.toString()}`)
}

export function createMaterialInbound(payload) {
  return authFetch('/api/warehouse/material-inbound', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
