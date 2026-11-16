import { authFetch } from './http.js'

export async function fetchEquipmentOeeKanban({ period = 'day', limit = 20 } = {}) {
  const params = new URLSearchParams({ period, limit: String(limit) })
  return authFetch(`/api/kanban/equipment-oee?${params}`, {}, '获取设备 OEE 看板数据失败')
}
