import { authFetch } from './http.js'

export async function fetchDevices({ page = 1, pageSize = 50, search, deviceTypeId, status } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (search) params.set('search', search)
  if (deviceTypeId) params.set('device_type_id', String(deviceTypeId))
  if (status) params.set('status', status)
  return authFetch(`/api/devices?${params}`)
}
