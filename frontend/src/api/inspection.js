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

export async function fetchInspectionDashboardStats(days = 7) {
  return authFetch(`/api/inspection/dashboard/stats?days=${days}`)
}

export async function fetchInspectionPlans({ page = 1, pageSize = 10, name, isActive, deviceTypeId } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (name) params.set('name', name)
  if (isActive !== undefined && isActive !== null && isActive !== '') {
    params.set('is_active', String(isActive))
  }
  if (deviceTypeId) params.set('device_type_id', String(deviceTypeId))
  return authFetch(`/api/inspection/plans?${params}`)
}

export async function createInspectionPlan(data) {
  return authFetch('/api/inspection/plans', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateInspectionPlan(id, data) {
  return authFetch(`/api/inspection/plans/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function toggleInspectionPlan(id) {
  return authFetch(`/api/inspection/plans/${id}/toggle`, { method: 'PATCH' })
}

export async function deleteInspectionPlan(id) {
  return authFetch(`/api/inspection/plans/${id}`, { method: 'DELETE' })
}

export async function fetchInspectionRecords({
  page = 1,
  pageSize = 10,
  search,
  status,
  dateFrom,
  dateTo,
  deviceId,
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (search) params.set('search', search)
  if (status) params.set('status', status)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (deviceId) params.set('device_id', String(deviceId))
  return authFetch(`/api/inspection/records?${params}`)
}

export async function fetchInspectionRecord(id) {
  return authFetch(`/api/inspection/records/${id}`)
}

export async function createInspectionRecord(data) {
  return authFetch('/api/inspection/records', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateInspectionRecord(id, data) {
  return authFetch(`/api/inspection/records/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function fetchPlanItemsForDevice(deviceId, planId) {
  const params = new URLSearchParams()
  if (planId) params.set('plan_id', String(planId))
  const qs = params.toString()
  return authFetch(`/api/inspection/plan-items/by-device/${deviceId}${qs ? `?${qs}` : ''}`)
}
