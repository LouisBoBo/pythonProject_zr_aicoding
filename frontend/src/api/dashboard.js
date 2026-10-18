import { authFetch } from './http.js'

export async function fetchDashboard() {
  return authFetch('/api/dashboard', {}, '获取仪表盘数据失败')
}

/** 工作台：四张汇总卡 + 待办 */
export async function fetchWorkbench({ todoType } = {}) {
  const params = new URLSearchParams()
  if (todoType) params.set('todo_type', todoType)
  const q = params.toString()
  const url = q ? `/api/dashboard/workbench?${q}` : '/api/dashboard/workbench'
  return authFetch(url, {}, '获取工作台数据失败')
}

/** 完成待办 */
export async function completeWorkbenchTodo(todoId) {
  return authFetch(
    `/api/dashboard/todos/${todoId}/complete`,
    { method: 'PATCH' },
    '完成待办失败',
  )
}
