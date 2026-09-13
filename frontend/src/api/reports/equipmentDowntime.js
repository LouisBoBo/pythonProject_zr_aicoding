import { appendPagination, authFetch, authFetchBlob } from './http.js'

export async function fetchEquipmentDowntimeFilters() {
  return authFetch('/api/reports/equipment-downtime/filters')
}

export async function fetchEquipmentDowntimeReport({
  page = 1,
  pageSize = 10,
  dateFrom,
  dateTo,
  workshop,
  equipmentType,
  equipmentId,
  status,
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (workshop) params.set('workshop', workshop)
  if (equipmentType) params.set('equipment_type', equipmentType)
  if (equipmentId) params.set('equipment_id', String(equipmentId))
  if (status) params.set('status', status)
  return authFetch(`/api/reports/equipment-downtime?${params}`)
}

export async function exportEquipmentDowntimeReport({
  dateFrom,
  dateTo,
  workshop,
  equipmentType,
  equipmentId,
  status,
} = {}) {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (workshop) params.set('workshop', workshop)
  if (equipmentType) params.set('equipment_type', equipmentType)
  if (equipmentId) params.set('equipment_id', String(equipmentId))
  if (status) params.set('status', status)
  return authFetchBlob(`/api/reports/equipment-downtime/export?${params}`)
}
