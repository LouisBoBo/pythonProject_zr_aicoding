<template>
  <div class="dashboard">
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <template v-else>
      <section class="stats-section">
        <div
          v-for="stat in displayStats"
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

      <div class="dashboard-grid">
        <section class="section-card chart-section">
          <h3 class="section-title">产量趋势</h3>
          <v-chart class="trend-chart" :option="chartOption" autoresize />
        </section>

        <section class="section-card orders-section">
          <h3 class="section-title">近期工单</h3>
          <el-table :data="recentOrders" stripe style="width: 100%">
            <el-table-column prop="id" label="工单号" width="140" />
            <el-table-column prop="title" label="标题" min-width="160" />
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="priority" label="优先级" width="90">
              <template #default="{ row }">
                <el-tag :type="priorityTagType(row.priority)" size="small" effect="plain">
                  {{ priorityLabel(row.priority) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="date" label="日期" width="110" />
          </el-table>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { Loading } from '@element-plus/icons-vue'
import { fetchDashboard } from '../../api/dashboard'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const router = useRouter()
const dashboard = ref(null)
const loading = ref(true)

const displayStats = computed(() => {
  if (!dashboard.value?.stats) return []
  return dashboard.value.stats.filter(
    (s) => s.key === 'today_output' || s.key === 'active_exceptions'
  ).concat(
    dashboard.value.stats.filter(
      (s) => s.key !== 'today_output' && s.key !== 'active_exceptions'
    ).slice(0, 2)
  )
})

const recentOrders = computed(() => {
  const todos = dashboard.value?.todos || []
  return todos.map((item) => ({
    id: item.link?.split('/').pop() || `WO-${item.id}`,
    title: item.title,
    status: item.type === 'exception' ? '异常' : item.type === 'timeout' ? '超时' : '待审',
    priority: item.priority,
    date: '2026-08-07',
  }))
})

const chartOption = computed(() => {
  const trend = dashboard.value?.production_trend || []
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 24, top: 24, bottom: 32 },
    xAxis: {
      type: 'category',
      data: trend.map((p) => p.date),
      axisLine: { lineStyle: { color: '#ddd' } },
      axisLabel: { color: '#888' },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      axisLabel: { color: '#888' },
    },
    series: [
      {
        name: '产量',
        type: 'line',
        smooth: true,
        data: trend.map((p) => p.output),
        lineStyle: { color: '#667eea', width: 2.5 },
        itemStyle: { color: '#667eea' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(102, 126, 234, 0.25)' },
              { offset: 1, color: 'rgba(102, 126, 234, 0.02)' },
            ],
          },
        },
      },
    ],
  }
})

function formatStatValue(stat) {
  if (stat.unit === '%') return `${stat.value}${stat.unit}`
  return `${stat.value} ${stat.unit}`.trim()
}

function priorityLabel(priority) {
  const labels = { high: '紧急', medium: '普通', low: '低' }
  return labels[priority] || priority
}

function statusTagType(status) {
  if (status === '异常') return 'danger'
  if (status === '超时') return 'warning'
  return 'info'
}

function priorityTagType(priority) {
  if (priority === 'high') return 'danger'
  if (priority === 'medium') return 'warning'
  return 'info'
}

onMounted(async () => {
  try {
    dashboard.value = await fetchDashboard()
  } catch {
    router.push('/login')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.dashboard {
  max-width: 1280px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 300px;
  color: #888;
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

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.section-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 16px;
}

.trend-chart {
  height: 280px;
  width: 100%;
}

@media (max-width: 1024px) {
  .stats-section {
    grid-template-columns: repeat(2, 1fr);
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .stats-section {
    grid-template-columns: 1fr;
  }
}
</style>
