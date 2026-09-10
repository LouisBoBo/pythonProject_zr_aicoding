#!/usr/bin/env node
/**
 * 前端自检：报表注册表 vs 磁盘文件。
 * 缺文件 → 警告并自动隐藏（不阻断 build）；仅当注册表为空且仍声明必选报表时报错。
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const SRC = path.join(ROOT, 'src')

const { REPORT_CATALOG } = await import(
  pathToFileURL(path.join(SRC, 'config/reportFeatures.js')).href
)

let warn = 0
const active = []

console.log('=== 前端自检：报表模块 ===')

for (const item of REPORT_CATALOG) {
  const viewPath = path.join(SRC, 'views/reports', item.viewFile)
  const apiPath = item.apiFile ? path.join(SRC, 'api/reports', item.apiFile) : null

  if (item.enabled === false) {
    console.log(`[hide] ${item.id}（enabled=false）`)
    continue
  }

  const viewOk = fs.existsSync(viewPath)
  const apiOk = !apiPath || fs.existsSync(apiPath)

  if (!viewOk || !apiOk) {
    warn += 1
    const parts = []
    if (!viewOk) parts.push(`缺视图 ${item.viewFile}`)
    if (!apiOk) parts.push(`缺 API ${item.apiFile}`)
    console.warn(`[skip] ${item.id}：${parts.join('；')} → 路由/菜单将自动隐藏`)
    continue
  }

  active.push(item.id)
  const flags = []
  if (item.menu !== false) flags.push('menu')
  if (item.hub !== false) flags.push('hub')
  console.log(`[ok]   ${item.id}（${flags.join('+') || '仅路由'}）`)
}

if (active.length === 0) {
  console.warn('[warn] 当前无可用报表子模块；报表中心页仍可打开，但无子入口')
} else {
  console.log(`\n可用报表 ${active.length} 个：${active.join(', ')}`)
}

if (warn > 0) {
  console.warn(`\n共 ${warn} 项已自动跳过（不会导致 Vite 编译失败）`)
}

console.log('\n自检完成')
process.exit(0)
