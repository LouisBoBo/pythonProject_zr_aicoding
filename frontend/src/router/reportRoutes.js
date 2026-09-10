import { REPORT_CATALOG } from '../config/reportFeatures.js'

/** Vite glob：仅打包实际存在的视图；删文件 = 自动从路由消失 */
const viewModules = import.meta.glob('../views/reports/*.vue')

const apiModules = import.meta.glob('../api/reports/*.js', { eager: true })

function viewKey(viewFile) {
  return `../views/reports/${viewFile}`
}

function apiExists(apiFile) {
  if (!apiFile) return true
  return Boolean(apiModules[`../api/reports/${apiFile}`])
}

function viewExists(viewFile) {
  return Boolean(viewModules[viewKey(viewFile)])
}

/** 解析当前可用的报表（enabled + 文件齐全） */
export function resolveReportFeatures() {
  const active = []
  const skipped = []

  for (const item of REPORT_CATALOG) {
    if (item.enabled === false) {
      skipped.push({ id: item.id, reason: 'enabled=false' })
      continue
    }
    if (!viewExists(item.viewFile)) {
      skipped.push({ id: item.id, reason: `缺少视图 ${item.viewFile}` })
      continue
    }
    if (!apiExists(item.apiFile)) {
      skipped.push({ id: item.id, reason: `缺少 API ${item.apiFile}` })
      continue
    }
    active.push(item)
  }

  return { active, skipped }
}

export function buildReportRoutes(authRequired) {
  const { active } = resolveReportFeatures()
  return active.map((item) => ({
    path: `reports/${item.routePath}`,
    name: `reports-${item.id}`,
    component: viewModules[viewKey(item.viewFile)],
    meta: { title: item.title, ...authRequired },
  }))
}

export function getReportMenuEntries() {
  return resolveReportFeatures().active
    .filter((item) => item.menu !== false)
    .map((item) => ({
      path: `/reports/${item.routePath}`,
      title: item.title,
      icon: item.icon,
    }))
}

export function getReportHubEntries() {
  return resolveReportFeatures().active
    .filter((item) => item.hub !== false)
    .map((item) => ({
      path: `/reports/${item.routePath}`,
      title: item.title,
      description: item.description,
      icon: item.icon,
    }))
}
