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
    const detail = error.detail
    const message = typeof detail === 'string' ? detail : '请求失败'
    throw new Error(message)
  }

  return response.json()
}

async function authFetchBlob(url, options = {}) {
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

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearToken()
    }
    const error = await response.json().catch(() => ({}))
    const detail = error.detail
    const message = typeof detail === 'string' ? detail : '导出失败'
    throw new Error(message)
  }

  return response.blob()
}

export async function fetchEquipmentList({
  page = 1,
  pageSize = 10,
  equipmentCode,
  name,
  department,
  status,
  search,
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (equipmentCode) params.set('equipment_code', equipmentCode)
  if (name) params.set('name', name)
  if (department) params.set('department', department)
  if (status) params.set('status', status)
  if (search) params.set('search', search)
  return authFetch(`/api/equipment?${params}`)
}

export async function fetchEquipment(id) {
  return authFetch(`/api/equipment/${id}`)
}

export async function createEquipment(data) {
  return authFetch('/api/equipment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateEquipment(id, data) {
  return authFetch(`/api/equipment/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function deleteEquipment(id) {
  return authFetch(`/api/equipment/${id}`, {
    method: 'DELETE',
  })
}

export async function importEquipment(file) {
  const token = getToken()
  if (!token) {
    throw new Error('未登录')
  }

  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch('/api/equipment/import', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  })

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearToken()
    }
    const error = await response.json().catch(() => ({}))
    const detail = error.detail
    const message = typeof detail === 'string' ? detail : '导入失败'
    throw new Error(message)
  }

  return response.json()
}

export async function exportEquipment(filters = {}) {
  const params = new URLSearchParams()
  if (filters.equipmentCode) params.set('equipment_code', filters.equipmentCode)
  if (filters.name) params.set('name', filters.name)
  if (filters.department) params.set('department', filters.department)
  if (filters.status) params.set('status', filters.status)
  if (filters.search) params.set('search', filters.search)

  const query = params.toString()
  const url = query ? `/api/equipment/export?${query}` : '/api/equipment/export'
  return authFetchBlob(url)
}
