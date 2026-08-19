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
    const detail = error.detail
    const message = typeof detail === 'string' ? detail : '请求失败'
    throw new Error(message)
  }

  return response.json()
}

export async function fetchMaintenancePlans({
  page = 1,
  pageSize = 10,
  search,
  status,
  equipmentId,
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (search) params.set('search', search)
  if (status) params.set('status', status)
  if (equipmentId) params.set('equipment_id', String(equipmentId))
  return authFetch(`/api/equipment-maintenance/plans?${params}`)
}

export async function fetchMaintenancePlan(id) {
  return authFetch(`/api/equipment-maintenance/plans/${id}`)
}

export async function createMaintenancePlan(data) {
  return authFetch('/api/equipment-maintenance/plans', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateMaintenancePlan(id, data) {
  return authFetch(`/api/equipment-maintenance/plans/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function deleteMaintenancePlan(id) {
  return authFetch(`/api/equipment-maintenance/plans/${id}`, { method: 'DELETE' })
}

export async function fetchMaintenanceOrders({
  page = 1,
  pageSize = 10,
  search,
  status,
  equipmentId,
  planId,
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (search) params.set('search', search)
  if (status) params.set('status', status)
  if (equipmentId) params.set('equipment_id', String(equipmentId))
  if (planId) params.set('plan_id', String(planId))
  return authFetch(`/api/equipment-maintenance/orders?${params}`)
}

export async function fetchMaintenanceOrder(id) {
  return authFetch(`/api/equipment-maintenance/orders/${id}`)
}

export async function createMaintenanceOrder(data) {
  return authFetch('/api/equipment-maintenance/orders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function generateOrderFromPlan(planId) {
  return authFetch(`/api/equipment-maintenance/orders/generate-from-plan/${planId}`, {
    method: 'POST',
  })
}

export async function dispatchMaintenanceOrder(id, data) {
  return authFetch(`/api/equipment-maintenance/orders/${id}/dispatch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function startMaintenanceOrder(id) {
  return authFetch(`/api/equipment-maintenance/orders/${id}/start`, { method: 'POST' })
}

export async function executeMaintenanceOrder(id, data) {
  return authFetch(`/api/equipment-maintenance/orders/${id}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateMaintenanceOrder(id, data) {
  return authFetch(`/api/equipment-maintenance/orders/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function deleteMaintenanceOrder(id) {
  return authFetch(`/api/equipment-maintenance/orders/${id}`, { method: 'DELETE' })
}

export async function fetchMaintenanceAlerts() {
  return authFetch('/api/equipment-maintenance/alerts')
}

export async function fetchEquipmentMaintenanceStatus(equipmentId) {
  return authFetch(`/api/equipment-maintenance/equipment/${equipmentId}/status`)
}
