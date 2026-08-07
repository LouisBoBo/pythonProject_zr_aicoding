import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '../api/auth'
import AppLayout from '../layouts/AppLayout.vue'
import LoginView from '../views/LoginView.vue'
import HomeIndex from '../views/home/Index.vue'
import FavoritesIndex from '../views/favorites/Index.vue'
import WorkbenchIndex from '../views/workbench/Index.vue'
import QualityIndex from '../views/quality/Index.vue'
import ProductionIndex from '../views/production/Index.vue'
import EquipmentIndex from '../views/equipment/Index.vue'
import WarehouseIndex from '../views/warehouse/Index.vue'
import ReportsIndex from '../views/reports/Index.vue'
import SettingsIndex from '../views/settings/Index.vue'
import MessagesIndex from '../views/messages/Index.vue'
import HelpIndex from '../views/help/Index.vue'
import WorkOrdersView from '../views/WorkOrdersView.vue'
import KanbanBoardsView from '../views/KanbanBoardsView.vue'
import ProductionKanbanView from '../views/kanban/ProductionKanbanView.vue'

const authRequired = { requiresAuth: true }

const kanbanRoutes = [
  { path: 'production', title: '生产看板', category: 'production' },
  { path: 'quality', title: '品质看板', category: 'quality' },
  { path: 'equipment', title: '设备看板', category: 'equipment' },
  { path: 'warehouse', title: '仓储看板', category: 'warehouse' },
  { path: 'general', title: '综合看板', category: 'general' },
]

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView },
    {
      path: '/',
      component: AppLayout,
      meta: authRequired,
      children: [
        { path: '', redirect: '/home' },
        { path: 'home', name: 'home', component: HomeIndex, meta: { title: '首页', ...authRequired } },
        { path: 'favorites', name: 'favorites', component: FavoritesIndex, meta: { title: '收藏夹', ...authRequired } },
        { path: 'workbench', name: 'workbench', component: WorkbenchIndex, meta: { title: '工作台', ...authRequired } },
        { path: 'quality', name: 'quality', component: QualityIndex, meta: { title: '品质分析', ...authRequired } },
        { path: 'quality/:id', name: 'quality-detail', component: QualityIndex, meta: { title: '品质分析', ...authRequired } },
        { path: 'production', name: 'production', component: ProductionIndex, meta: { title: '生产管理', ...authRequired } },
        { path: 'production-plan/:id?', name: 'production-plan', component: ProductionIndex, meta: { title: '生产管理', ...authRequired } },
        { path: 'equipment', name: 'equipment', component: EquipmentIndex, meta: { title: '设备管理', ...authRequired } },
        { path: 'equipment/:id', name: 'equipment-detail', component: EquipmentIndex, meta: { title: '设备管理', ...authRequired } },
        { path: 'warehouse', name: 'warehouse', component: WarehouseIndex, meta: { title: '仓储管理', ...authRequired } },
        { path: 'warehouse/:id', name: 'warehouse-detail', component: WarehouseIndex, meta: { title: '仓储管理', ...authRequired } },
        { path: 'reports', name: 'reports', component: ReportsIndex, meta: { title: '报表中心', ...authRequired } },
        { path: 'settings', name: 'settings', component: SettingsIndex, meta: { title: '系统设置', ...authRequired } },
        { path: 'messages', name: 'messages', component: MessagesIndex, meta: { title: '消息中心', ...authRequired } },
        { path: 'help', name: 'help', component: HelpIndex, meta: { title: '帮助文档', ...authRequired } },
        {
          path: 'work-orders/new',
          redirect: { path: '/work-orders', query: { create: '1' } },
        },
        {
          path: 'work-orders/:id?',
          name: 'work-orders',
          component: WorkOrdersView,
          meta: { title: '生产工单', ...authRequired },
        },
        {
          path: 'kanban-boards/new',
          redirect: { path: '/kanban/production', query: { create: '1' } },
        },
        {
          path: 'kanban-boards/:id?',
          redirect: '/kanban/production',
        },
        ...kanbanRoutes.map(({ path, title, category }) => ({
          path: `kanban/${path}`,
          name: `kanban-${path}`,
          component: path === 'production' ? ProductionKanbanView : KanbanBoardsView,
          meta: { title, category, ...authRequired },
        })),
        {
          path: 'kanban',
          redirect: '/kanban/production',
        },
        { path: 'dashboard', redirect: '/home' },
      ],
    },
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
