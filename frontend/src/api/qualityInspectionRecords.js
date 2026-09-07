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
    throw new Error(error.detail || '请求失败')
  }

  return response.json()
}

export function fetchQualityInspectionRecords({
  page = 1,
  pageSize = 10,
  inspectionNo,
  inspectionType,
  inspectionResult,
  workOrderNo,
  batchNo,
  materialCode,
  materialName,
  inspector,
  dateFrom,
  dateTo,
} = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  if (inspectionNo) params.set('inspection_no', inspectionNo)
  if (inspectionType) params.set('inspection_type', inspectionType)
  if (inspectionResult) params.set('inspection_result', inspectionResult)
  if (workOrderNo) params.set('work_order_no', workOrderNo)
  if (batchNo) params.set('batch_no', batchNo)
  if (materialCode) params.set('material_code', materialCode)
  if (materialName) params.set('material_name', materialName)
  if (inspector) params.set('inspector', inspector)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return authFetch(`/api/quality/inspection-records?${params.toString()}`)
}
