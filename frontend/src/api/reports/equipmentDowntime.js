import { appendPagination, authFetch, authFetchBlob } from './http.js'

export async function fetchEquipmentDowntimeFilters() {
  return authFetch('/api/reports/equipment-downtime/filters')
}

export async function fetchEquipmentDowntimeReport({
  page = 1,
  pageSize = 10,
  period,
  dateFrom,
  dateTo,
  workshop,
  equipmentType,
  equipmentId,
  downtimeReason,
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (period) params.set('period', period)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (workshop) params.set('workshop', workshop)
  if (equipmentType) params.set('equipment_type', equipmentType)
  if (equipmentId) params.set('equipment_id', String(equipmentId))
  if (downtimeReason) params.set('downtime_reason', downtimeReason)
  return authFetch(`/api/reports/equipment-downtime?${params}`)
}

export async function exportEquipmentDowntimeReport({
  period,
  dateFrom,
  dateTo,
  workshop,
  equipmentType,
  equipmentId,
  downtimeReason,
} = {}) {
  const params = new URLSearchParams()
  if (period) params.set('period', period)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (workshop) params.set('workshop', workshop)
  if (equipmentType) params.set('equipment_type', equipmentType)
  if (equipmentId) params.set('equipment_id', String(equipmentId))
  if (downtimeReason) params.set('downtime_reason', downtimeReason)
  return authFetchBlob(`/api/reports/equipment-downtime/export?${params}`)
}
