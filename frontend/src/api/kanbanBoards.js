import { authFetch } from './http.js'

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
