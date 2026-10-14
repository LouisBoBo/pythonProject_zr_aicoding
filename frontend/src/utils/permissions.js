/** 前端权限辅助：与后端 permissions 码对齐 */

export function isAdminRole(role) {
  return String(role || '').toLowerCase() === 'admin'
}

export function hasPermission(user, code) {
  if (!code) return true
  if (!user) return false
  if (isAdminRole(user.role)) return true
  const list = Array.isArray(user.permissions) ? user.permissions : []
  return list.includes(code)
}

/**
 * 递归过滤菜单：无 permission 字段则默认可见；有则需具备权限。
 */
export function filterMenuByPermissions(groups, user) {
  if (!Array.isArray(groups)) return []
  return groups
    .map((group) => {
      const items = (group.items || [])
        .map((item) => filterMenuItem(item, user))
        .filter(Boolean)
      if (!items.length) return null
      return { ...group, items }
    })
    .filter(Boolean)
}

function filterMenuItem(item, user) {
  if (!item) return null
  if (item.children?.length) {
    const children = item.children.map((c) => filterMenuItem(c, user)).filter(Boolean)
    if (!children.length) return null
    if (item.permission && !hasPermission(user, item.permission)) return null
    return { ...item, children }
  }
  if (item.permission && !hasPermission(user, item.permission)) return null
  return item
}
