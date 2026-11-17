import { authFetch } from './http.js'

export function fetchMaterialList({
  page = 1,
  pageSize = 10,
  materialCode,
  materialName,
  category,
} = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  if (materialCode) params.set('material_code', materialCode)
  if (materialName) params.set('material_name', materialName)
  if (category) params.set('category', category)
  return authFetch(`/api/materials?${params.toString()}`)
}

export function createMaterial(payload) {
  return authFetch('/api/materials', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function updateMaterial(id, payload) {
  return authFetch(`/api/materials/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function deleteMaterial(id) {
  return authFetch(`/api/materials/${id}`, { method: 'DELETE' })
}
