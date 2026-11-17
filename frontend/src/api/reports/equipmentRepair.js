import { appendPagination, authFetch, authFetchBlob } from './http.js'

export async function fetchEquipmentRepairReport({
  page = 1,
  pageSize = 10,
  keyword,
  status,
  dateFrom,
  dateTo,
  equipmentCode,
  faultCategory,
} = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page, pageSize })
  if (keyword) params.set('keyword', keyword)
  if (status) params.set('status', status)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (equipmentCode) params.set('equipment_code', equipmentCode)
  if (faultCategory) params.set('fault_category', faultCategory)
  return authFetch(`/api/reports/equipment-repairs?${params}`)
}

export async function fetchEquipmentRepairReportDetail(repairId) {
  return authFetch(`/api/reports/equipment-repairs/${repairId}`)
}

export async function exportEquipmentRepairReport({
  keyword,
  status,
  dateFrom,
  dateTo,
  equipmentCode,
  faultCategory,
} = {}) {
  const params = new URLSearchParams()
  if (keyword) params.set('keyword', keyword)
  if (status) params.set('status', status)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (equipmentCode) params.set('equipment_code', equipmentCode)
  if (faultCategory) params.set('fault_category', faultCategory)
  return authFetchBlob(`/api/reports/equipment-repairs/export?${params}`)
}
