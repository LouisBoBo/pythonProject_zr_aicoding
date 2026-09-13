import { appendPagination, authFetch, authFetchBlob } from './http.js'

export async function fetchEquipmentMetricsFilters() {
  return authFetch('/api/reports/equipment-metrics/filters')
}

export async function fetchEquipmentMetricsReport({
  page = 1,
  pageSize = 10,
  dateFrom,
  dateTo,
  workshop,
  equipmentType,
  equipmentId,
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (workshop) params.set('workshop', workshop)
  if (equipmentType) params.set('equipment_type', equipmentType)
  if (equipmentId != null) params.set('equipment_id', String(equipmentId))
  return authFetch(`/api/reports/equipment-metrics?${params}`)
}

export async function exportEquipmentMetricsReport({
  dateFrom,
  dateTo,
  workshop,
  equipmentType,
  equipmentId,
} = {}) {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (workshop) params.set('workshop', workshop)
  if (equipmentType) params.set('equipment_type', equipmentType)
  if (equipmentId != null) params.set('equipment_id', String(equipmentId))
  return authFetchBlob(`/api/reports/equipment-metrics/export?${params}`)
}
