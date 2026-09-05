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

export function fetchMaterialOutboundList({
  page = 1,
  pageSize = 10,
  outboundNo,
  materialCode,
  materialName,
  batchNo,
  receiverDepartment,
  status,
  dateFrom,
  dateTo,
} = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  if (outboundNo) params.set('outbound_no', outboundNo)
  if (materialCode) params.set('material_code', materialCode)
  if (materialName) params.set('material_name', materialName)
  if (batchNo) params.set('batch_no', batchNo)
  if (receiverDepartment) params.set('receiver_department', receiverDepartment)
  if (status) params.set('status', status)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return authFetch(`/api/work-orders/material-outbound?${params.toString()}`)
}

export function fetchMaterialOutboundStockBalance({ materialId, warehouseId, locationId } = {}) {
  const params = new URLSearchParams()
  params.set('material_id', String(materialId))
  params.set('warehouse_id', String(warehouseId))
  if (locationId) params.set('location_id', String(locationId))
  return authFetch(`/api/work-orders/material-outbound/stock-balance?${params.toString()}`)
}

export function createMaterialOutbound(payload) {
  return authFetch('/api/work-orders/material-outbound', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
