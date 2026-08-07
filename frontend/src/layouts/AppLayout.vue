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
            <li v-for="item in group.items" :key="item.path">
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
          <el-input
            v-model="searchKeyword"
            placeholder="搜索功能、工单..."
            class="search-input"
            clearable
            :prefix-icon="Search"
          />
          <el-dropdown trigger="click" @command="handleUserCommand">
            <div class="user-dropdown">
              <el-avatar :size="32" class="user-avatar">
                {{ userInitial }}
              </el-avatar>
              <span class="user-name">{{ user?.username || '用户' }}</span>
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
      { path: '/production', title: '生产管理', icon: SetUp },
      { path: '/equipment', title: '设备管理', icon: Cpu },
      { path: '/warehouse', title: '仓储管理', icon: Box },
    ],
  },
  {
    key: 'system',
    title: '系统',
    items: [
      { path: '/reports', title: '报表中心', icon: DataLine },
      { path: '/settings', title: '系统设置', icon: Setting },
      { path: '/messages', title: '消息中心', icon: Bell },
      { path: '/help', title: '帮助文档', icon: QuestionFilled },
    ],
  },
]

const currentTitle = computed(() => route.meta.title || '首页')

const topTabs = [
  { label: '首页', path: '/home' },
  { label: '工作台', path: '/workbench' },
  { label: '生产管理', path: '/production' },
  { label: '品质分析', path: '/quality' },
  { label: '报表中心', path: '/reports' },
]

const activeTab = computed(() => {
  const match = topTabs.find(
    (tab) => route.path === tab.path || route.path.startsWith(tab.path + '/'),
  )
  return match?.path || '/home'
})

function handleTabChange(path) {
  if (path && path !== route.path) {
    router.push(path)
  }
}

const userInitial = computed(() => {
  const name = user.value?.username || 'U'
  return name.charAt(0).toUpperCase()
})

function toggleGroup(key) {
  expandedGroups[key] = !expandedGroups[key]
}

function isActive(path) {
  if (path === '/home') {
    return route.path === '/home' || route.path === '/'
  }
  return route.path === path || route.path.startsWith(path + '/')
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
  min-height: 100vh;
  background: #f0f2f5;
}

.sidebar {
  width: 220px;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease;
  flex-shrink: 0;
  position: relative;
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
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  gap: 16px;
}

.topbar-left {
  flex: 1;
  min-width: 0;
}

.top-tabs {
  --el-tabs-header-height: 40px;
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
  color: #666;
  padding: 0 18px;
  height: 40px;
  line-height: 40px;
}

.top-tabs :deep(.el-tabs__item.is-active) {
  color: #667eea;
  font-weight: 600;
}

.top-tabs :deep(.el-tabs__active-bar) {
  background-color: #667eea;
  height: 3px;
  border-radius: 2px;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-input {
  width: 240px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background 0.2s;
}

.user-dropdown:hover {
  background: #f5f6fa;
}

.user-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-weight: 600;
}

.user-name {
  font-size: 14px;
  color: #444;
}

.content-area {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}
</style>
