import { authFetch } from './http.js'

export async function fetchMaintenanceRecords({
  page = 1,
  pageSize = 10,
  keyword,
  maintenanceType,
  maintenanceResult,
  equipmentId,
  dateFrom,
  dateTo,
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (keyword) params.set('keyword', keyword)
  if (maintenanceType) params.set('maintenance_type', maintenanceType)
  if (maintenanceResult) params.set('maintenance_result', maintenanceResult)
  if (equipmentId) params.set('equipment_id', String(equipmentId))
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return authFetch(`/api/equipment-maintenance-records?${params}`)
}

export async function fetchMaintenanceRecordDetail(id) {
  return authFetch(`/api/equipment-maintenance-records/${id}`)
}

export async function createMaintenanceRecord(data) {
  return authFetch('/api/equipment-maintenance-records', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateMaintenanceRecord(id, data) {
  return authFetch(`/api/equipment-maintenance-records/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function deleteMaintenanceRecord(id) {
  return authFetch(`/api/equipment-maintenance-records/${id}`, { method: 'DELETE' })
}
