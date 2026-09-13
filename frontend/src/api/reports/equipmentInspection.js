import { appendPagination, authFetch } from './http.js'

export async function fetchEquipmentInspectionFilters() {
  return authFetch('/api/reports/equipment-inspection/filters')
}

export async function fetchEquipmentInspectionReport({
  page = 1,
  pageSize = 10,
  dateFrom,
  dateTo,
  deviceId,
  workshop,
  status,
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (deviceId) params.set('device_id', String(deviceId))
  if (workshop) params.set('workshop', workshop)
  if (status) params.set('status', status)
  return authFetch(`/api/reports/equipment-inspection?${params}`)
}
