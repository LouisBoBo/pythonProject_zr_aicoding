/** 页面收藏（按登录用户隔离 localStorage） */
const BASE_KEY = 'erp_page_favorites_v1'
export const FAVORITES_MAX = 30

export function favoritesStorageKey(username) {
  const u = String(username || '').trim() || 'anon'
  return `${BASE_KEY}:${u}`
}

function normalizeItem(raw, index) {
  const url = String((raw && (raw.url != null ? raw.url : raw.path)) || '').trim()
  let title = ''
  if (raw && raw.title != null && String(raw.title).trim()) {
    title = String(raw.title).trim()
  } else if (raw && raw.name != null && String(raw.name).trim()) {
    title = String(raw.name).trim()
  } else {
    title = url || '未命名'
  }
  if (!url) return null
  const created =
    (raw && (raw.created_at != null ? raw.created_at : raw.createdAt)) || null
  return {
    id: (raw && raw.id) || `${url}-${index}`,
    title,
    url,
    created_at: created,
  }
}

export function readFavorites(username) {
  const key = favoritesStorageKey(username)
  try {
    const raw = localStorage.getItem(key)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed)) return []
      return parsed.map((entry, i) => normalizeItem(entry, i)).filter(Boolean)
    }
    // 兼容旧版全局 key → 迁入当前账号一次
    const legacy = localStorage.getItem(BASE_KEY)
    if (!legacy) return []
    const parsed = JSON.parse(legacy)
    if (!Array.isArray(parsed) || !parsed.length) return []
    const migrated = parsed.map((entry, i) => normalizeItem(entry, i)).filter(Boolean)
    writeFavorites(username, migrated)
    return migrated
  } catch {
    return []
  }
}

export function writeFavorites(username, list) {
  const clean = (Array.isArray(list) ? list : [])
    .map((entry, i) => normalizeItem(entry, i))
    .filter(Boolean)
    .slice(0, FAVORITES_MAX)
  localStorage.setItem(
    favoritesStorageKey(username),
    JSON.stringify(
      clean.map(({ title, url, created_at }) => ({ title, url, created_at })),
    ),
  )
  return clean
}

export function isFavorited(username, url) {
  const u = String(url || '').trim()
  if (!u) return false
  return readFavorites(username).some((item) => item.url === u)
}

/**
 * 收藏当前页：同 path 去重置顶；超过上限丢弃最旧。
 * @returns {{ ok: boolean, reason?: string, list: array }}
 */
export function addFavorite(username, { title, url }) {
  const path = String(url || '').trim()
  if (!path) return { ok: false, reason: 'empty_url', list: readFavorites(username) }
  const name = String(title || path).trim() || '未命名'
  let list = readFavorites(username).filter((item) => item.url !== path)
  list.unshift({
    id: path,
    title: name,
    url: path,
    created_at: new Date().toISOString(),
  })
  if (list.length > FAVORITES_MAX) {
    list = list.slice(0, FAVORITES_MAX)
  }
  writeFavorites(username, list)
  return { ok: true, list }
}

export function removeFavoriteByUrl(username, url) {
  const path = String(url || '').trim()
  const list = readFavorites(username).filter((item) => item.url !== path)
  writeFavorites(username, list)
  return list
}

export function removeFavoriteById(username, id) {
  const list = readFavorites(username).filter((item) => item.id !== id)
  writeFavorites(username, list)
  return list
}
