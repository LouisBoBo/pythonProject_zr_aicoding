import { authFetch } from './http.js'

/** SPC 筛选项 */
export async function fetchSpcFilters() {
  return authFetch('/api/quality/spc/filters')
}

/** SPC 控制图列表 */
export async function fetchSpcCharts({ processName, characteristic, chartType } = {}) {
  const params = new URLSearchParams()
  if (processName) params.set('process_name', processName)
  if (characteristic) params.set('characteristic', characteristic)
  if (chartType) params.set('chart_type', chartType)
  const q = params.toString()
  return authFetch(`/api/quality/spc/charts${q ? `?${q}` : ''}`)
}

/** SPC 控制图详情（只读） */
export async function fetchSpcChartDetail(chartId) {
  return authFetch(`/api/quality/spc/charts/${chartId}`)
}

/** 重新计算并持久化控制限（需写权限） */
export async function recomputeSpcChart(chartId) {
  return authFetch(`/api/quality/spc/charts/${chartId}/recompute`, {
    method: 'POST',
  })
}

/** 临时计算控制限 */
export async function computeSpc(body) {
  return authFetch('/api/quality/spc/compute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}
