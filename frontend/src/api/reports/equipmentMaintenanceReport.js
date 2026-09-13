import { appendPagination, authFetch, authFetchBlob } from './http.js'

export async function fetchEquipmentMaintenanceReport({
  page = 1,
  pageSize = 10,
  keyword,
  status,
  dateFrom,
  dateTo,
  equipmentCode,
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (keyword) params.set('keyword', keyword)
  if (status) params.set('status', status)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (equipmentCode) params.set('equipment_code', equipmentCode)
  return authFetch(`/api/reports/equipment-maintenance?${params}`)
}

export async function exportEquipmentMaintenanceReport({
  keyword,
  status,
  dateFrom,
  dateTo,
  equipmentCode,
} = {}) {
  const params = new URLSearchParams()
  if (keyword) params.set('keyword', keyword)
  if (status) params.set('status', status)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (equipmentCode) params.set('equipment_code', equipmentCode)
  return authFetchBlob(`/api/reports/equipment-maintenance/export?${params}`)
}
