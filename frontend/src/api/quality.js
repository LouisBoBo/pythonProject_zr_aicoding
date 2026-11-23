import { authFetch } from './http.js'

export async function fetchQualityKpi(period = 'day') {
  return authFetch(`/api/quality/kpi?period=${period}`)
}

export async function fetchQualityTrend(granularity = 'day', days = 30) {
  return authFetch(`/api/quality/trend?granularity=${granularity}&days=${days}`)
}

export async function fetchProcessYield() {
  return authFetch('/api/quality/process-yield')
}

export async function fetchDefectDistribution(by = 'type') {
  return authFetch(`/api/quality/defect-distribution?by=${by}`)
}

export async function fetchQualityAnomalies(status = 'open', limit = 20) {
  return authFetch(`/api/quality/anomalies?status=${status}&limit=${limit}`)
}

export async function fetchQualityAnomaliesList({ status, page = 1, pageSize = 10 } = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  if (status) {
    params.set('status', status)
  }
  return authFetch(`/api/quality/anomalies?${params.toString()}`)
}

/** 关闭品质异常 */
export async function closeQualityAnomaly(anomalyId, { handler, resolutionNote }) {
  return authFetch(`/api/quality/anomalies/${anomalyId}/close`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      handler,
      resolution_note: resolutionNote,
    }),
  })
}

export async function fetchTopDefects(limit = 10) {
  return authFetch(`/api/quality/top-defects?limit=${limit}`)
}

/** IPQC 四维分析（工序合格率 / 日趋势 / 客户 Top / 审核时效） */
export async function fetchIpqcAnalytics({ dateFrom, dateTo, customerTop = 10 } = {}) {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (customerTop) params.set('customer_top', String(customerTop))
  const q = params.toString()
  return authFetch(`/api/quality/ipqc-analytics${q ? `?${q}` : ''}`)
}
