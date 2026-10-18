import { authFetch } from './http'

/** 顶栏全局搜索；短关键字由调用方拦截，不发起请求 */
export async function globalSearch(q) {
  const keyword = String(q || '').trim()
  const params = new URLSearchParams({ q: keyword })
  return authFetch(`/api/search?${params}`, {}, '全局搜索失败')
}
