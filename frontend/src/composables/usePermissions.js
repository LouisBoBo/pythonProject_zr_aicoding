import { computed, inject, unref } from 'vue'
import { hasPermission as checkPermission, isAdminRole } from '../utils/permissions'

export const CURRENT_USER_KEY = 'erpCurrentUser'

/**
 * 读取布局 provide 的当前用户，判断权限。
 * @returns {{ user: import('vue').ComputedRef, can: (code: string) => boolean, isAdmin: import('vue').ComputedRef<boolean> }}
 */
export function usePermissions() {
  const userRef = inject(CURRENT_USER_KEY, null)

  const user = computed(() => {
    if (!userRef) return null
    return unref(userRef)
  })

  const isAdmin = computed(() => isAdminRole(user.value?.role))

  function can(code) {
    return checkPermission(user.value, code)
  }

  return { user, can, isAdmin }
}
