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

export async function fetchKanbanBoards({
  page = 1,
  pageSize = 10,
  status,
  category,
  productionLine,
  boardCode,
  boardName,
  search,
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (status) params.set('status', status)
  if (category) params.set('category', category)
  if (productionLine) params.set('production_line', productionLine)
  if (boardCode) params.set('board_code', boardCode)
  if (boardName) params.set('board_name', boardName)
  if (search) params.set('search', search)
  return authFetch(`/api/kanban-boards?${params}`)
}

export async function fetchKanbanBoard(id) {
  return authFetch(`/api/kanban-boards/${id}`)
}

export async function createKanbanBoard(data) {
  return authFetch('/api/kanban-boards', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateKanbanBoard(id, data) {
  return authFetch(`/api/kanban-boards/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateKanbanBoardStatus(id, status) {
  return authFetch(`/api/kanban-boards/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
}

export async function deleteKanbanBoard(id) {
  return authFetch(`/api/kanban-boards/${id}`, {
    method: 'DELETE',
  })
}
