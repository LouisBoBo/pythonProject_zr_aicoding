<template>
  <div class="app-layout">
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-logo">
        <span class="logo-icon">E</span>
        <span v-if="!sidebarCollapsed" class="logo-text">ERP 系统</span>
      </div>

      <nav class="sidebar-nav">
        <template v-for="group in menuGroups" :key="group.key">
          <div
            v-if="group.title && !sidebarCollapsed"
            class="nav-group-title"
            @click="toggleGroup(group.key)"
          >
            <span>{{ group.title }}</span>
            <el-icon class="group-arrow" :class="{ expanded: expandedGroups[group.key] }">
              <ArrowDown />
            </el-icon>
          </div>
          <ul
            v-show="sidebarCollapsed || !group.title || expandedGroups[group.key]"
            class="nav-list"
          >
            <template v-for="item in group.items" :key="item.path || item.key">
              <li v-if="item.children" class="nav-submenu">
                <div
                  class="nav-item nav-parent"
                  :class="{ active: isSubmenuActive(item), expanded: expandedSubmenus[item.key] }"
                  @click="toggleSubmenu(item.key)"
                >
                  <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
                  <span v-if="!sidebarCollapsed" class="nav-label">{{ item.title }}</span>
                  <el-icon v-if="!sidebarCollapsed" class="submenu-arrow">
                    <ArrowDown />
                  </el-icon>
                </div>
                <ul
                  v-show="!sidebarCollapsed && expandedSubmenus[item.key]"
                  class="nav-sublist"
                >
                  <li v-for="child in item.children" :key="child.path">
                    <router-link
                      :to="child.path"
                      class="nav-item nav-child"
                      :class="{ active: isChildActive(child.path) }"
                    >
                      <el-icon class="nav-icon"><component :is="child.icon" /></el-icon>
                      <span class="nav-label">{{ child.title }}</span>
                    </router-link>
                  </li>
                </ul>
              </li>
              <li v-else>
                <router-link
                  :to="item.path"
                  class="nav-item"
                  :class="{ active: isActive(item.path) }"
                  :title="sidebarCollapsed ? item.title : ''"
                >
                  <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
                  <span v-if="!sidebarCollapsed" class="nav-label">{{ item.title }}</span>
                </router-link>
              </li>
            </template>
          </ul>
        </template>
      </nav>

      <button class="collapse-btn" @click="sidebarCollapsed = !sidebarCollapsed">
        <el-icon><component :is="sidebarCollapsed ? Expand : Fold" /></el-icon>
      </button>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <el-tabs
            :model-value="activeTab"
            class="top-tabs"
            @tab-change="handleTabChange"
          >
            <el-tab-pane
              v-for="tab in topTabs"
              :key="tab.path"
              :label="tab.label"
              :name="tab.path"
            />
          </el-tabs>
        </div>

        <div class="topbar-right">
          <div class="search-group">
            <el-input
              v-model="searchKeyword"
              placeholder="请输入"
              class="search-input"
              clearable
              @keyup.enter="handleSearch"
            />
            <el-button class="search-btn" :icon="Search" @click="handleSearch" />
          </div>
          <el-dropdown trigger="click" class="org-dropdown">
            <div class="org-selector">
              <el-icon class="org-lock"><Lock /></el-icon>
              <span>多组织</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>默认组织</el-dropdown-item>
                <el-dropdown-item>华东工厂</el-dropdown-item>
                <el-dropdown-item>华南工厂</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-dropdown trigger="click" @command="handleUserCommand">
            <div class="user-dropdown">
              <el-avatar :size="32" class="user-avatar">
                {{ userInitial }}
              </el-avatar>
              <span class="user-name">{{ user?.username || '李杰' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  {{ user?.role || '操作员' }}
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <div v-if="showPageTab" class="page-tab-bar">
        <span class="page-tab active">{{ currentTitle }}</span>
        <div class="page-tab-actions">
          <el-icon><MoreFilled /></el-icon>
          <el-icon><Refresh /></el-icon>
          <el-icon><ArrowDown /></el-icon>
          <el-icon><FullScreen /></el-icon>
        </div>
      </div>

      <main class="content-area">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  Expand,
  Fold,
  Search,
  Lock,
  MoreFilled,
  Refresh,
  FullScreen,
  HomeFilled,
  Star,
  Monitor,
  DataAnalysis,
  SetUp,
  Cpu,
  Box,
  DataLine,
  Setting,
  Bell,
  QuestionFilled,
  Document,
  Grid,
  List,
  Calendar,
  Tools,
} from '@element-plus/icons-vue'
import { clearToken, fetchCurrentUser } from '../api/auth'

const router = useRouter()
const route = useRoute()

const sidebarCollapsed = ref(false)
const searchKeyword = ref('')
const user = ref(null)

const expandedGroups = reactive({
  overview: true,
  business: true,
  system: true,
})

const expandedSubmenus = reactive({
  production: true,
  kanban: true,
  equipment: true,
  warehouse: true,
  reports: true,
})

const menuGroups = [
  {
    key: 'overview',
    title: '概览',
    items: [
      { path: '/home', title: '首页', icon: HomeFilled },
      { path: '/favorites', title: '收藏夹', icon: Star },
      { path: '/workbench', title: '工作台', icon: Monitor },
    ],
  },
  {
    key: 'business',
    title: '业务管理',
    items: [
      { path: '/quality', title: '品质分析', icon: DataAnalysis },
      {
        key: 'production',
        title: '生产管理',
        icon: SetUp,
        children: [
          { path: '/production', title: '生产概览', icon: SetUp },
          { path: '/work-orders', title: '生产工单', icon: Document },
        ],
      },
      {
        key: 'kanban',
        title: '看板管理',
        icon: Grid,
        children: [
          { path: '/kanban/production', title: '生产看板', icon: SetUp },
          { path: '/quality/dashboard', title: '品质看板', icon: DataAnalysis },
          { path: '/kanban/equipment', title: '设备看板', icon: Cpu },
          { path: '/kanban/warehouse', title: '仓储看板', icon: Box },
          { path: '/kanban/general', title: '综合看板', icon: DataLine },
        ],
      },
      {
        key: 'equipment',
        title: '设备管理',
        icon: Cpu,
        children: [
          { path: '/equipment/ledger', title: '设备台账', icon: Cpu },
          { path: '/equipment/inspection', title: '设备点检', icon: List },
          { path: '/equipment/maintenance-plans', title: '保养计划', icon: Calendar },
          { path: '/equipment/maintenance-orders', title: '保养工单', icon: Tools },
          { path: '/equipment/repairs', title: '维修管理', icon: SetUp },
        ],
      },
      {
        key: 'warehouse',
        title: '仓储管理',
        icon: Box,
        children: [
          { path: '/warehouse/inventory', title: '物料库存', icon: Box },
          { path: '/warehouse/inbound', title: '物料入库', icon: List },
        ],
      },
    ],
  },
  {
    key: 'system',
    title: '系统',
    items: [
      {
        key: 'reports',
        title: '报表中心',
        icon: DataLine,
        children: [
          { path: '/reports/wip', title: '在制品报表', icon: Document },
        ],
      },
      { path: '/settings', title: '系统设置', icon: Setting },
      { path: '/messages', title: '消息中心', icon: Bell },
      { path: '/help', title: '帮助文档', icon: QuestionFilled },
    ],
  },
]

const currentTitle = computed(() => route.meta.title || '首页')

const topTabs = [
  { label: '首页', path: '/home' },
  { label: '收藏夹', path: '/favorites' },
  { label: '工作台', path: '/workbench' },
  { label: '品质分析', path: '/quality' },
]

const activeTab = computed(() => {
  const match = topTabs.find(
    (tab) => route.path === tab.path || route.path.startsWith(tab.path + '/'),
  )
  return match?.path || '/home'
})

const showPageTab = computed(
  () =>
    route.path === '/home' ||
    route.path === '/' ||
    route.path === '/production' ||
    route.path.startsWith('/production-plan'),
)

function handleTabChange(path) {
  if (path && path !== route.path) {
    router.push(path)
  }
}

function handleSearch() {
  if (searchKeyword.value.trim()) {
    // placeholder for future search integration
  }
}

const userInitial = computed(() => {
  const name = user.value?.username || '李'
  return name.charAt(0).toUpperCase()
})

function toggleGroup(key) {
  expandedGroups[key] = !expandedGroups[key]
}

function toggleSubmenu(key) {
  expandedSubmenus[key] = !expandedSubmenus[key]
}

function isSubmenuActive(item) {
  return item.children?.some((child) => isActive(child.path))
}

function isActive(path) {
  if (path === '/home') {
    return route.path === '/home' || route.path === '/'
  }
  return route.path === path || route.path.startsWith(path + '/')
}

function isChildActive(path) {
  if (route.path === path) return true
  if (!route.path.startsWith(path + '/')) return false
  if (path === '/equipment/ledger' && route.path.startsWith('/equipment/inspection')) {
    return false
  }
  if (path === '/equipment/ledger' && route.path.startsWith('/equipment/maintenance-')) {
    return false
  }
  if (path === '/equipment/ledger' && route.path.startsWith('/equipment/repairs')) {
    return false
  }
  if (path === '/equipment/ledger' && route.path.startsWith('/equipment/ledger/')) {
    return true
  }
  return true
}

function handleUserCommand(command) {
  if (command === 'logout') {
    clearToken()
    router.push('/login')
  }
}

onMounted(async () => {
  try {
    user.value = await fetchCurrentUser()
  } catch {
    router.push('/login')
  }
})
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: #f0f2f5;
}

.sidebar {
  width: 220px;
  height: 100%;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 16px;
  flex-shrink: 0;
}

.logo-text {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.sidebar-nav {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 0;
}

.nav-group-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  user-select: none;
}

.group-arrow {
  transition: transform 0.2s;
}

.group-arrow.expanded {
  transform: rotate(0deg);
}

.group-arrow:not(.expanded) {
  transform: rotate(-90deg);
}

.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 12px;
}

.nav-item:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.06);
}

.nav-item.active {
  color: #fff;
  background: rgba(102, 126, 234, 0.25);
  border-left-color: #667eea;
}

.nav-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.nav-label {
  white-space: nowrap;
}

.nav-submenu {
  list-style: none;
}

.nav-parent {
  cursor: pointer;
  position: relative;
}

.submenu-arrow {
  margin-left: auto;
  font-size: 12px;
  transition: transform 0.2s;
}

.nav-parent.expanded .submenu-arrow {
  transform: rotate(180deg);
}

.nav-sublist {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-child {
  padding-left: 48px !important;
  font-size: 13px;
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: none;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s;
}

.collapse-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #3d3d3d;
  gap: 16px;
  min-height: 48px;
}

.topbar-left {
  flex: 1;
  min-width: 0;
}

.top-tabs {
  --el-tabs-header-height: 48px;
}

.top-tabs :deep(.el-tabs__header) {
  margin: 0;
  border-bottom: none;
}

.top-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.top-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.65);
  padding: 0 18px;
  height: 48px;
  line-height: 48px;
}

.top-tabs :deep(.el-tabs__item.is-active) {
  color: #fff;
  font-weight: 500;
}

.top-tabs :deep(.el-tabs__active-bar) {
  background-color: #409eff;
  height: 2px;
  border-radius: 0;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-group {
  display: flex;
  align-items: center;
  gap: 0;
}

.search-input {
  width: 160px;
}

.search-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.12);
  box-shadow: none;
  border-radius: 4px 0 0 4px;
  border: none;
}

.search-btn {
  border-radius: 0 4px 4px 0;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: rgba(255, 255, 255, 0.85);
  height: 32px;
  padding: 0 10px;
}

.search-btn:hover {
  background: rgba(255, 255, 255, 0.28);
  color: #fff;
}

.search-input :deep(.el-input__inner) {
  color: #fff;
}

.search-input :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.45);
}

.search-input :deep(.el-input__prefix .el-icon) {
  color: rgba(255, 255, 255, 0.5);
}

.org-selector {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.85);
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}

.org-selector:hover {
  background: rgba(255, 255, 255, 0.16);
}

.org-lock {
  font-size: 14px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
  color: rgba(255, 255, 255, 0.85);
}

.user-dropdown:hover {
  background: rgba(255, 255, 255, 0.1);
}

.user-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-weight: 600;
}

.user-name {
  font-size: 14px;
}

.page-tab-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  min-height: 40px;
}

.page-tab {
  font-size: 14px;
  color: #666;
  padding: 10px 0;
  position: relative;
}

.page-tab.active {
  color: #409eff;
  font-weight: 500;
}

.page-tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: #409eff;
}

.page-tab-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  color: #999;
  font-size: 16px;
}

.page-tab-actions .el-icon {
  cursor: pointer;
}

.page-tab-actions .el-icon:hover {
  color: #666;
}

.content-area {
  flex: 1;
  min-height: 0;
  padding: 16px 20px;
  overflow-y: auto;
  overflow-x: hidden;
  background: #f0f2f5;
}
</style>
