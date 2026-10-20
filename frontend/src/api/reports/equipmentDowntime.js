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
  equipmentId,
  downtimeReason,
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (workshop) params.set('workshop', workshop)
  if (equipmentId) params.set('equipment_id', String(equipmentId))
  if (downtimeReason) params.set('downtime_reason', downtimeReason)
  return authFetch(`/api/reports/equipment-downtime?${params}`)
}

export async function exportEquipmentDowntimeReport({
  dateFrom,
  dateTo,
  workshop,
  equipmentId,
  downtimeReason,
} = {}) {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (workshop) params.set('workshop', workshop)
  if (equipmentId) params.set('equipment_id', String(equipmentId))
  if (downtimeReason) params.set('downtime_reason', downtimeReason)
  return authFetchBlob(`/api/reports/equipment-downtime/export?${params}`)
}
