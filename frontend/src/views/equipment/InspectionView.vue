<template>
  <div class="equipment-inspection-page">
    <header class="page-header">
      <div class="header-main">
        <span class="header-badge">EQUIP · INSPECTION</span>
        <h1 class="header-title">设备点检</h1>
      </div>
      <nav class="section-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="section-tab"
          :class="{ active: activeTab === tab.key }"
          @click="switchTab(tab.key)"
        >
          <el-icon><component :is="tab.icon" /></el-icon>
          <span>{{ tab.label }}</span>
        </button>
      </nav>
    </header>

    <div class="section-content" :class="{ 'section-content--dashboard': activeTab === 'dashboard' }">
      <InspectionDashboard v-if="activeTab === 'dashboard'" />
      <InspectionRecords v-else-if="activeTab === 'records'" />
      <InspectionExecute v-else-if="activeTab === 'execute'" />
      <InspectionPlans v-else-if="activeTab === 'plans'" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Calendar, DataLine, Document, EditPen } from '@element-plus/icons-vue'
import InspectionDashboard from '../inspection/DashboardView.vue'
import InspectionRecords from '../inspection/RecordsView.vue'
import InspectionExecute from '../inspection/ExecuteView.vue'
import InspectionPlans from '../inspection/PlansView.vue'

const route = useRoute()
const router = useRouter()

const tabs = [
  { key: 'dashboard', label: '统计看板', icon: DataLine },
  { key: 'records', label: '点检记录', icon: Document },
  { key: 'execute', label: '执行点检', icon: EditPen },
  { key: 'plans', label: '点检计划', icon: Calendar },
]

const activeTab = computed(() => {
  const tab = route.query.tab
  return tabs.some((t) => t.key === tab) ? tab : 'dashboard'
})

function switchTab(key) {
  if (key === activeTab.value) return
  const query = { tab: key }
  if (key === 'records') {
    if (route.query.status) query.status = route.query.status
    if (route.query.detail) query.detail = route.query.detail
  }
  router.replace({ path: '/equipment/inspection', query })
}
</script>

<style scoped>
.equipment-inspection-page {
  margin: -16px -20px;
  min-height: calc(100vh - 72px);
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
}

.page-header {
  background: #1a2332;
  border-bottom: 1px solid rgba(49, 130, 206, 0.35);
  padding: 16px 24px 0;
  flex-shrink: 0;
}

.header-badge {
  display: inline-block;
  font-size: 10px;
  letter-spacing: 1.5px;
  color: #4299e1;
  margin-bottom: 4px;
}

.header-title {
  margin: 0 0 14px;
  font-size: 20px;
  font-weight: 600;
  color: #fff;
}

.section-tabs {
  display: flex;
  gap: 4px;
}

.section-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.55);
  font-size: 14px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}

.section-tab:hover {
  color: rgba(255, 255, 255, 0.85);
}

.section-tab.active {
  color: #4299e1;
  border-bottom-color: #4299e1;
}

.section-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 20px;
}

.section-content--dashboard {
  padding: 0;
  overflow: hidden;
}

.section-content--dashboard :deep(.inspection-dashboard) {
  margin: 0;
  min-height: calc(100vh - 130px);
}
</style>
