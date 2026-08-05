import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '../api/auth'
import LoginView from '../views/LoginView.vue'
import HomeView from '../views/HomeView.vue'
import PlaceholderView from '../views/PlaceholderView.vue'

const authRequired = { requiresAuth: true }

const moduleRoutes = [
  { path: '/work-orders/:id?', name: 'work-orders', meta: { title: '工单管理', ...authRequired } },
  { path: '/production-plan/:id?', name: 'production-plan', meta: { title: '生产计划', ...authRequired } },
  { path: '/quality/:id?', name: 'quality', meta: { title: '品质管理', ...authRequired } },
  { path: '/warehouse/:id?', name: 'warehouse', meta: { title: '仓储管理', ...authRequired } },
  { path: '/equipment/:id?', name: 'equipment', meta: { title: '设备管理', ...authRequired } },
  { path: '/reports', name: 'reports', meta: { title: '报表中心', ...authRequired } },
]

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/home' },
    { path: '/login', name: 'login', component: LoginView },
    {
      path: '/home',
      name: 'home',
      component: HomeView,
      meta: { requiresAuth: true },
    },
    {
      path: '/dashboard',
      redirect: '/home',
    },
    ...moduleRoutes.map((route) => ({
      ...route,
      component: PlaceholderView,
    })),
  ],
})

router.beforeEach((to) => {
  const token = getToken()
  if (to.meta.requiresAuth && !token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && token) {
    return { name: 'home' }
  }
})

export default router
