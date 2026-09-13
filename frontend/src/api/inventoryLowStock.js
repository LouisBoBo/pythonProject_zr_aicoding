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

/** 库存低水位预警列表 */
export function fetchInventoryLowStockList({ page = 1, size = 10, warehouseName, keyword } = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('size', String(size))
  if (warehouseName) params.set('warehouse_name', warehouseName)
  if (keyword) params.set('keyword', keyword)
  return authFetch(`/api/inventory-low-stock?${params.toString()}`)
}
