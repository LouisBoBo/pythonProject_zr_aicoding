import { authFetch } from './http.js'

export function fetchQualityInspectionTasks({
  page = 1,
  pageSize = 10,
  inspectionNo,
  inspectionType,
  status,
  workOrderNo,
  productCode,
  batchNo,
  materialCode,
  inspector,
} = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  if (inspectionNo) params.set('inspection_no', inspectionNo)
  if (inspectionType) params.set('inspection_type', inspectionType)
  if (status) params.set('status', status)
  if (workOrderNo) params.set('work_order_no', workOrderNo)
  if (productCode) params.set('product_code', productCode)
  if (batchNo) params.set('batch_no', batchNo)
  if (materialCode) params.set('material_code', materialCode)
  if (inspector) params.set('inspector', inspector)
  return authFetch(`/api/quality/inspection-tasks?${params.toString()}`)
}

export function updateQualityInspectionTaskStatus(taskId, status) {
  return authFetch(`/api/quality/inspection-tasks/${taskId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
}
