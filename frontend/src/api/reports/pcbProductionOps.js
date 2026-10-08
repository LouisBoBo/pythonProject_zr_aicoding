import { authFetch } from './http.js'

export async function fetchPcbProductionOpsReport({ days = 7 } = {}) {
  const params = new URLSearchParams()
  if (days) params.set('days', String(days))
  const qs = params.toString()
  return authFetch(`/api/reports/pcb-production-ops${qs ? `?${qs}` : ''}`)
}
