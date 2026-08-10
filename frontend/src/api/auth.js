const TOKEN_KEY = 'erp_access_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

function parseApiErrorDetail(detail, fallback = '登录失败') {
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || item?.message || '')
      .filter(Boolean)
      .join('；') || fallback
  }
  if (typeof detail === 'object' && detail.message) return detail.message
  return fallback
}

export async function login(username, password, enterpriseCode) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username,
      password,
      enterprise_code: enterpriseCode,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(parseApiErrorDetail(error.detail, '登录失败'))
  }

  const data = await response.json()
  setToken(data.access_token)
  return data
}

export async function fetchCurrentUser() {
  const token = getToken()
  if (!token) {
    throw new Error('未登录')
  }

  const response = await fetch('/api/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    clearToken()
    throw new Error('登录已过期')
  }

  return response.json()
}
