import { clearToken, getToken } from './auth'

async function authFetch(url, options = {}) {
  const token = getToken()
  if (!token) {
    throw new Error('未登录')
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  })

  if (response.status === 204) {
    return null
  }

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      clearToken()
    }
    const error = await response.json().catch(() => ({}))
    const detail = error.detail
    const message = typeof detail === 'string' ? detail : '请求失败'
    throw new Error(message)
  }

  return response.json()
}

/** 未读消息总数（侧边栏角标） */
export function fetchUnreadCount() {
  return authFetch('/api/messages/unread-count')
}

/** 分页消息列表 */
export function fetchMessageList({ page = 1, size = 20, category, level, isRead, keyword } = {}) {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('size', String(size))
  if (category) params.set('category', category)
  if (level) params.set('level', level)
  if (isRead !== undefined && isRead !== null && isRead !== '') {
    params.set('is_read', String(isRead))
  }
  if (keyword) params.set('keyword', keyword)
  return authFetch(`/api/messages?${params.toString()}`)
}

/** 获取消息详情 */
export function fetchMessageDetail(id) {
  return authFetch(`/api/messages/${id}`)
}

/** 标记单条已读 */
export function markMessageRead(id) {
  return authFetch(`/api/messages/${id}/read`, { method: 'POST' })
}

/** 全部标记为已读，可按分类筛选 */
export function markAllMessagesRead({ category } = {}) {
  const params = new URLSearchParams()
  if (category) params.set('category', category)
  const query = params.toString()
  const url = query ? `/api/messages/read-all?${query}` : '/api/messages/read-all'
  return authFetch(url, { method: 'PATCH' })
}

/** 新建消息 */
export function createMessage(data) {
  return authFetch('/api/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

/** 更新消息 */
export function updateMessage(id, data) {
  return authFetch(`/api/messages/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

/** 删除消息 */
export function deleteMessage(id) {
  return authFetch(`/api/messages/${id}`, {
    method: 'DELETE',
  })
}
