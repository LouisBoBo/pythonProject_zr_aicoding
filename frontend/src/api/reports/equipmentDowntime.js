import { appendPagination, authFetch } from './http.js'

export async function fetchEquipmentDowntimeFilters() {
  return authFetch('/api/reports/equipment-downtime/filters')
}

export async function fetchEquipmentDowntimeReport({
  page = 1,
  pageSize = 10,
  dateFrom,
  dateTo,
  workshop,
  productionLine,
  equipmentId,
  downtimeReason,
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (workshop) params.set('workshop', workshop)
  if (productionLine) params.set('production_line', productionLine)
  if (equipmentId) params.set('equipment_id', String(equipmentId))
  if (downtimeReason) params.set('downtime_reason', downtimeReason)
  return authFetch(`/api/reports/equipment-downtime?${params}`)
}