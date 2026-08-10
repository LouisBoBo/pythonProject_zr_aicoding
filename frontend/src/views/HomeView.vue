<template>
  <div class="home-page">
    <header class="header">
      <h1>ERP 系统首页</h1>
      <div class="user-info" v-if="user">
        <span>{{ user.username }} ({{ user.role }})</span>
        <button class="logout-btn" @click="handleLogout">退出登录</button>
      </div>
    </header>

    <main class="content" v-if="!loading">
      <!-- 统计面板 -->
      <section class="stats-section">
        <div
          v-for="stat in dashboard?.stats"
          :key="stat.key"
          class="stat-card"
        >
          <span class="stat-label">{{ stat.label }}</span>
          <div class="stat-value-row">
            <span class="stat-value">{{ formatStatValue(stat) }}</span>
            <span v-if="stat.trend" class="stat-trend">{{ stat.trend }}</span>
          </div>
        </div>
      </section>

      <div class="main-grid">
        <div class="primary-column">
          <!-- 导航入口卡片 -->
          <section class="section-card">
            <h2 class="section-title">业务模块</h2>
            <div class="module-grid">
              <router-link
                v-for="mod in modules"
                :key="mod.route"
                :to="mod.route"
                class="module-card"
              >
                <span class="module-icon">{{ mod.icon }}</span>
                <span class="module-name">{{ mod.name }}</span>
                <span class="module-desc">{{ mod.desc }}</span>
              </router-link>
            </div>
          </section>

          <!-- 图表区 -->
          <section class="charts-row">
            <div class="section-card chart-card">
              <h2 class="section-title">生产趋势</h2>
              <svg
                v-if="dashboard?.production_trend?.length"
                class="line-chart"
                viewBox="0 0 400 180"
                preserveAspectRatio="xMidYMid meet"
              >
                <polyline
                  :points="lineChartPoints"
                  fill="none"
                  stroke="#667eea"
                  stroke-width="2.5"
                  stroke-linejoin="round"
                />
                <circle
                  v-for="(point, idx) in chartCoords"
                  :key="idx"
                  :cx="point.x"
                  :cy="point.y"
                  r="4"
                  fill="#667eea"
                />
                <text
                  v-for="(point, idx) in chartCoords"
                  :key="'label-' + idx"
                  :x="point.x"
                  y="175"
                  text-anchor="middle"
                  class="chart-label"
                >
                  {{ dashboard.production_trend[idx].date }}
                </text>
              </svg>
            </div>

            <div class="section-card chart-card">
              <h2 class="section-title">工单状态分布</h2>
              <div class="bar-chart" v-if="dashboard?.work_order_status?.length">
                <div
                  v-for="item in dashboard.work_order_status"
                  :key="item.status"
                  class="bar-row"
                >
                  <span class="bar-label">{{ item.status }}</span>
                  <div class="bar-track">
                    <div
                      class="bar-fill"
                      :style="{ width: barWidth(item.count) + '%' }"
                    />
                  </div>
                  <span class="bar-count">{{ item.count }}</span>
                </div>
              </div>
            </div>
          </section>
        </div>

        <aside class="sidebar">
          <!-- 快捷入口 -->
          <section class="section-card">
            <h2 class="section-title">快捷入口</h2>
            <div class="quick-links">
              <router-link
                v-for="link in quickLinks"
                :key="link.route"
                :to="link.route"
                class="quick-link"
              >
                <span class="quick-icon">{{ link.icon }}</span>
                <span>{{ link.name }}</span>
              </router-link>
            </div>
          </section>

          <!-- 待办/异常列表 -->
          <section class="section-card todo-section">
            <h2 class="section-title">待办事项</h2>
            <ul class="todo-list" v-if="dashboard?.todos?.length">
              <li
                v-for="item in dashboard.todos"
                :key="item.id"
                class="todo-item"
              >
                <router-link :to="item.link" class="todo-link">
                  <span class="todo-priority" :class="'priority-' + item.priority">
                    {{ priorityLabel(item.priority) }}
                  </span>
                  <span class="todo-title">{{ item.title }}</span>
                  <span class="todo-desc">{{ item.description }}</span>
                </router-link>
              </li>
            </ul>
            <p v-else class="empty-hint">暂无待办事项</p>
          </section>
        </aside>
      </div>
    </main>

    <div v-else class="loading-state">加载中...</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { clearToken, fetchCurrentUser } from '../api/auth'
import { fetchDashboard } from '../api/dashboard'

const router = useRouter()
const user = ref(null)
const dashboard = ref(null)
const loading = ref(true)

const modules = [
  {
    name: '工单管理',
    desc: '创建、跟踪与关闭生产工单',
    route: '/work-orders',
    icon: '📋',
  },
  {
    name: '生产计划',
    desc: '排程编制与产能规划',
    route: '/production-plan',
    icon: '📅',
  },
  {
    name: '品质管理',
    desc: '质检记录与异常追踪',
    route: '/quality',
    icon: '✅',
  },
  {
    name: '仓储管理',
    desc: '入库出库与库存盘点',
    route: '/warehouse',
    icon: '📦',
  },
  {
    name: '设备管理',
    desc: '设备台账与维护保养',
    route: '/equipment/ledger',
    icon: '⚙️',
  },
  {
    name: '报表中心',
    desc: '数据统计与可视化报表',
    route: '/reports',
    icon: '📊',
  },
]

const quickLinks = [
  { name: '新建工单', route: '/work-orders?create=1', icon: '➕' },
  { name: '今日排程', route: '/production-plan', icon: '🗓️' },
  { name: '异常上报', route: '/quality', icon: '⚠️' },
  { name: '库存查询', route: '/warehouse', icon: '🔍' },
]

const CHART_WIDTH = 360
const CHART_HEIGHT = 140
const CHART_PADDING = 20

const chartCoords = computed(() => {
  const trend = dashboard.value?.production_trend
  if (!trend?.length) return []

  const outputs = trend.map((p) => p.output)
  const min = Math.min(...outputs)
  const max = Math.max(...outputs)
  const range = max - min || 1
  const step = CHART_WIDTH / (trend.length - 1 || 1)

  return trend.map((point, idx) => ({
    x: CHART_PADDING + idx * step,
    y: CHART_PADDING + CHART_HEIGHT - ((point.output - min) / range) * CHART_HEIGHT,
  }))
})

const lineChartPoints = computed(() =>
  chartCoords.value.map((p) => `${p.x},${p.y}`).join(' ')
)

const maxOrderCount = computed(() => {
  const items = dashboard.value?.work_order_status
  if (!items?.length) return 1
  return Math.max(...items.map((i) => i.count))
})

function barWidth(count) {
  return (count / maxOrderCount.value) * 100
}

function formatStatValue(stat) {
  if (stat.unit === '%') {
    return `${stat.value}${stat.unit}`
  }
  return `${stat.value} ${stat.unit}`.trim()
}

function priorityLabel(priority) {
  const labels = { high: '紧急', medium: '普通', low: '低' }
  return labels[priority] || priority
}

onMounted(async () => {
  try {
    user.value = await fetchCurrentUser()
    dashboard.value = await fetchDashboard()
  } catch {
    router.push('/login')
  } finally {
    loading.value = false
  }
})

function handleLogout() {
  clearToken()
  router.push('/login')
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.header h1 {
  font-size: 20px;
  color: #1a1a2e;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
  color: #555;
}

.logout-btn {
  padding: 6px 16px;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.logout-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.content {
  flex: 1;
  padding: 24px 32px 32px;
  max-width: 1280px;
  margin: 0 auto;
  width: 100%;
}

.loading-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
  font-size: 16px;
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.stat-label {
  display: block;
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
}

.stat-trend {
  font-size: 13px;
  color: #667eea;
  font-weight: 500;
}

.main-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
}

.section-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  margin-bottom: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 16px;
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.module-card {
  display: flex;
  flex-direction: column;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 10px;
  text-decoration: none;
  transition: all 0.2s;
  cursor: pointer;
}

.module-card:hover {
  border-color: #667eea;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.15);
  transform: translateY(-2px);
}

.module-icon {
  font-size: 28px;
  margin-bottom: 10px;
}

.module-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 4px;
}

.module-desc {
  font-size: 12px;
  color: #888;
  line-height: 1.4;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-card {
  margin-bottom: 0;
}

.line-chart {
  width: 100%;
  height: 180px;
}

.chart-label {
  font-size: 10px;
  fill: #888;
}

.bar-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar-label {
  width: 56px;
  font-size: 13px;
  color: #555;
  flex-shrink: 0;
}

.bar-track {
  flex: 1;
  height: 20px;
  background: #f0f2f5;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.bar-count {
  width: 32px;
  font-size: 13px;
  font-weight: 600;
  color: #1a1a2e;
  text-align: right;
}

.quick-links {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quick-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  text-decoration: none;
  color: #444;
  font-size: 14px;
  transition: background 0.2s;
}

.quick-link:hover {
  background: #f5f6fa;
  color: #667eea;
}

.quick-icon {
  font-size: 16px;
}

.todo-section {
  margin-bottom: 0;
}

.todo-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.todo-item {
  border-bottom: 1px solid #f0f0f0;
}

.todo-item:last-child {
  border-bottom: none;
}

.todo-link {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 0;
  text-decoration: none;
  transition: opacity 0.2s;
}

.todo-link:hover {
  opacity: 0.8;
}

.todo-priority {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  width: fit-content;
}

.priority-high {
  background: #fed7d7;
  color: #c53030;
}

.priority-medium {
  background: #fefcbf;
  color: #975a16;
}

.priority-low {
  background: #e2e8f0;
  color: #4a5568;
}

.todo-title {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a2e;
}

.todo-desc {
  font-size: 12px;
  color: #888;
  line-height: 1.4;
}

.empty-hint {
  color: #aaa;
  font-size: 14px;
  text-align: center;
  padding: 16px 0;
}

@media (max-width: 1024px) {
  .stats-section {
    grid-template-columns: repeat(2, 1fr);
  }

  .main-grid {
    grid-template-columns: 1fr;
  }

  .module-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .charts-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .stats-section {
    grid-template-columns: 1fr;
  }

  .module-grid {
    grid-template-columns: 1fr;
  }

  .content {
    padding: 16px;
  }
}
</style>
