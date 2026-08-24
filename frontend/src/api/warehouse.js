import { clearToken, getToken } from './auth'

async function authFetch(url, options = {}) {
  const token = getToken()
  if (!token) {
    throw new Error('未登录')
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  })

  if (response.status === 204) {
    return null
  }

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearToken()
    }
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || '请求失败')
  }

  return response.json()
}

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
