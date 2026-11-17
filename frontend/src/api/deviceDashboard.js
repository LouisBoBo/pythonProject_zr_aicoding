import { authFetch } from './http.js'

export function fetchDeviceStatusSummary() {
  return authFetch('/api/device/status/summary')
}

export function fetchDeviceOEE() {
  return authFetch('/api/device/oee')
}

export function fetchDeviceDashboardList({ page = 1, pageSize = 20, status = '' } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (status && status !== '全部') params.set('status', status)
  return authFetch(`/api/device/list?${params}`)
}

export function fetchDeviceUtilization(period = 'day') {
  return authFetch(`/api/device/utilization?period=${period}`)
}

export function fetchDeviceAlarmsTrend() {
  return authFetch('/api/device/alarms/trend')
}

export function fetchDeviceOutput() {
  return authFetch('/api/device/output')
}
