import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '../api/auth'
import AppLayout from '../layouts/AppLayout.vue'
import LoginView from '../views/LoginView.vue'
import HomeIndex from '../views/home/Index.vue'
import FavoritesIndex from '../views/favorites/Index.vue'
import WorkbenchIndex from '../views/workbench/Index.vue'
import QualityIndex from '../views/quality/Index.vue'
import QualityDashboardView from '../views/quality/DashboardView.vue'
import ProductionIndex from '../views/production/Index.vue'
import MaterialOutboundView from '../views/warehouse/MaterialOutboundView.vue'
import EquipmentInspection from '../views/equipment/InspectionView.vue'
import EquipmentLedgerView from '../views/equipment/EquipmentLedgerView.vue'
import EquipmentDetailView from '../views/equipment/EquipmentDetailView.vue'
import MaintenancePlansView from '../views/equipment/MaintenancePlansView.vue'
import MaintenanceOrdersView from '../views/equipment/MaintenanceOrdersView.vue'
import RepairManagement from '../views/equipment/RepairManagement.vue'
import RepairDetail from '../views/equipment/RepairDetail.vue'
import MaterialInventoryView from '../views/warehouse/MaterialInventoryView.vue'
import MaterialInboundListView from '../views/warehouse/MaterialInboundListView.vue'
import ReportsIndex from '../views/reports/Index.vue'
import WipReportView from '../views/reports/WipReportView.vue'
import DailyOutputReportView from '../views/reports/DailyOutputReportView.vue'
import QualityAnomaliesReportView from '../views/reports/QualityAnomaliesReportView.vue'
import EquipmentReportView from '../views/reports/EquipmentReportView.vue'
import EmployeeWorkHoursReportView from '../views/reports/EmployeeWorkHoursReportView.vue'
import EquipmentRepairReportView from '../views/reports/EquipmentRepairReportView.vue'
import SettingsIndex from '../views/settings/Index.vue'
import MessagesIndex from '../views/messages/Index.vue'
import HelpIndex from '../views/help/Index.vue'
import WorkOrdersView from '../views/WorkOrdersView.vue'
import KanbanBoardsView from '../views/KanbanBoardsView.vue'
import ProductionKanbanView from '../views/kanban/ProductionKanbanView.vue'
import ComprehensiveKanbanView from '../views/kanban/ComprehensiveKanbanView.vue'
import DeviceDashboard from '../views/board/DeviceDashboard.vue'
import WarehouseDashboard from '../views/board/WarehouseDashboard.vue'
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
        { path: 'quality/dashboard', name: 'quality-dashboard', component: QualityDashboardView, meta: { title: '品质看板', ...authRequired } },
        { path: 'quality/:id', name: 'quality-detail', component: QualityIndex, meta: { title: '品质分析', ...authRequired } },
        { path: 'production', name: 'production', component: ProductionIndex, meta: { title: '生产概览', ...authRequired } },
        { path: 'production-plan/:id?', name: 'production-plan', component: ProductionIndex, meta: { title: '生产概览', ...authRequired } },
        { path: 'equipment', redirect: '/equipment/ledger' },
        {
          path: 'equipment/ledger',
          name: 'equipment-ledger',
          component: EquipmentLedgerView,
          meta: { title: '设备台账', ...authRequired },
        },
        {
          path: 'equipment/ledger/:id',
          name: 'equipment-ledger-detail',
          component: EquipmentDetailView,
          meta: { title: '设备详情', ...authRequired },
        },
        { path: 'equipment/inspection', name: 'equipment-inspection', component: EquipmentInspection, meta: { title: '设备点检', ...authRequired } },
        {
          path: 'equipment/maintenance-plans',
          name: 'equipment-maintenance-plans',
          component: MaintenancePlansView,
          meta: { title: '保养计划', ...authRequired },
        },
        {
          path: 'equipment/maintenance-orders',
          name: 'equipment-maintenance-orders',
          component: MaintenanceOrdersView,
          meta: { title: '保养工单', ...authRequired },
        },
        {
          path: 'equipment/repairs',
          name: 'equipment-repairs',
          component: RepairManagement,
          meta: { title: '维修管理', ...authRequired },
        },
        {
          path: 'equipment/repairs/:id',
          name: 'equipment-repair-detail',
          component: RepairDetail,
          meta: { title: '维修详情', ...authRequired },
        },
        { path: 'inspection/dashboard', redirect: { path: '/equipment/inspection', query: { tab: 'dashboard' } } },
        { path: 'inspection/records', redirect: (to) => ({ path: '/equipment/inspection', query: { tab: 'records', ...to.query } }) },
        { path: 'inspection/execute', redirect: { path: '/equipment/inspection', query: { tab: 'execute' } } },
        { path: 'inspection/plans', redirect: { path: '/equipment/inspection', query: { tab: 'plans' } } },
        { path: 'inspection', redirect: { path: '/equipment/inspection', query: { tab: 'dashboard' } } },
        { path: 'warehouse', redirect: '/warehouse/inventory' },
        {
          path: 'warehouse/inventory',
          name: 'warehouse-inventory',
          component: MaterialInventoryView,
          meta: { title: '物料库存', ...authRequired },
        },
        {
          path: 'warehouse/inbound',
          name: 'warehouse-inbound',
          component: MaterialInboundListView,
          meta: { title: '物料入库', ...authRequired },
        },
        {
          path: 'warehouse/outbound',
          name: 'warehouse-material-outbound',
          component: MaterialOutboundView,
          meta: { title: '物料出库', ...authRequired },
        },
        { path: 'warehouse/:id', redirect: '/warehouse/inventory' },
        { path: 'reports', name: 'reports', component: ReportsIndex, meta: { title: '报表中心', ...authRequired } },
        { path: 'reports/wip', name: 'reports-wip', component: WipReportView, meta: { title: '在制品报表', ...authRequired } },
        {
          path: 'reports/daily-output',
          name: 'reports-daily-output',
          component: DailyOutputReportView,
          meta: { title: '日产报表', ...authRequired },
        },
        {
          path: 'reports/quality-anomalies',
          name: 'reports-quality-anomalies',
          component: QualityAnomaliesReportView,
          meta: { title: '质量管理', ...authRequired },
        },
        {
          path: 'reports/equipment',
          name: 'reports-equipment',
          component: EquipmentReportView,
          meta: { title: '设备管理', ...authRequired },
        },
        {
          path: 'reports/employee-work-hours',
          name: 'reports-employee-work-hours',
          component: EmployeeWorkHoursReportView,
          meta: { title: '员工工时', ...authRequired },
        },
        {
          path: 'reports/equipment-repairs',
          name: 'reports-equipment-repairs',
          component: EquipmentRepairReportView,
          meta: { title: '设备维修', ...authRequired },
        },
        { path: 'settings', name: 'settings', component: SettingsIndex, meta: { title: '系统设置', ...authRequired } },
        { path: 'messages', name: 'messages', component: MessagesIndex, meta: { title: '消息中心', ...authRequired } },
        { path: 'messages/:tab', redirect: '/messages' },
        { path: 'help', name: 'help', component: HelpIndex, meta: { title: '帮助文档', ...authRequired } },
        {
          path: 'work-orders/new',
          redirect: { path: '/work-orders', query: { create: '1' } },
        },
        {
          path: 'work-orders/:id?',
          name: 'work-orders',
          component: WorkOrdersView,
          meta: { title: '生产工单', ...authRequired } },
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
          component:
            path === 'production' ? ProductionKanbanView
            : path === 'quality' ? QualityDashboardView
            : path === 'equipment' ? DeviceDashboard
            : path === 'warehouse' ? WarehouseDashboard
            : path === 'general' ? ComprehensiveKanbanView
            : KanbanBoardsView,
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
