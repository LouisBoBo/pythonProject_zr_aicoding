import { authFetch } from './http.js'

export function fetchMaterialPurchaseList({
  page = 1,
  pageSize = 10,
  materialCode,
  materialName,
  supplierName,
} = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  if (materialCode) params.set('material_code', materialCode)
  if (materialName) params.set('material_name', materialName)
  if (supplierName) params.set('supplier_name', supplierName)
  return authFetch(`/api/material-purchases?${params.toString()}`)
}
