<template>
  <div v-loading="loading" class="inspection-dashboard">
    <header class="dash-header">
      <div class="header-left">
        <span class="header-badge">INSPECTION</span>
        <h1 class="header-title">点检统计看板</h1>
        <span class="header-date">{{ todayLabel }}</span>
      </div>
      <div class="header-right">
        <span class="header-rate-label">今日完成率</span>
        <span class="header-rate-value">{{ stats.completion_rate }}%</span>
      </div>
    </header>

    <section class="kpi-row">
      <div class="kpi-panel kpi-due">
        <div class="kpi-ring-wrap">
          <v-chart class="kpi-ring" :option="dueRingOption" autoresize />
          <div class="kpi-ring-center">
            <span class="kpi-num">{{ stats.today_due }}</span>
            <span class="kpi-unit">台</span>
          </div>
        </div>
        <div class="kpi-meta">
          <span class="kpi-label">今日应检</span>
          <span class="kpi-sub">计划覆盖全部活跃设备</span>
        </div>
      </div>

      <div class="kpi-panel kpi-done">
        <div class="kpi-ring-wrap">
          <v-chart class="kpi-ring" :option="doneRingOption" autoresize />
          <div class="kpi-ring-center">
            <span class="kpi-num">{{ stats.today_completed }}</span>
            <span class="kpi-unit">台</span>
          </div>
        </div>
        <div class="kpi-meta">
          <span class="kpi-label">今日已检</span>
          <span class="kpi-sub">正常 + 异常已提交</span>
        </div>
      </div>

      <div class="kpi-panel kpi-abnormal">
        <div class="kpi-ring-wrap">
          <v-chart class="kpi-ring" :option="abnormalRingOption" autoresize />
          <div class="kpi-ring-center abnormal-center">
            <span class="kpi-num abnormal-num">{{ stats.today_abnormal }}</span>
            <span class="kpi-unit">项</span>
          </div>
        </div>
        <div class="kpi-meta">
          <span class="kpi-label abnormal-label">今日异常</span>
          <span class="kpi-sub">需跟进处理</span>
        </div>
      </div>
    </section>

    <section class="chart-row">
      <div class="chart-panel trend-panel">
        <div class="panel-head">
          <span class="panel-title">本月完成率趋势</span>
          <div class="period-switch">
            <button
              :class="{ active: trendDays === 7 }"
              @click="switchTrend(7)"
            >
              7天
            </button>
            <button
              :class="{ active: trendDays === 30 }"
              @click="switchTrend(30)"
            >
              30天
            </button>
          </div>
        </div>
        <v-chart class="trend-chart" :option="trendLineOption" autoresize />
      </div>

      <div class="chart-panel type-panel">
        <div class="panel-head">
          <span class="panel-title">各设备类型点检完成率</span>
          <span class="panel-hint">近30天</span>
        </div>
        <v-chart class="type-chart" :option="typeBarOption" autoresize />
      </div>
    </section>

    <section class="abnormal-section">
      <div class="panel-head">
        <span class="panel-title">最近异常记录</span>
        <router-link to="/inspection/records?status=abnormal" class="view-all">
          查看全部 →
        </router-link>
      </div>
      <ul v-if="stats.recent_abnormals.length" class="abnormal-list">
        <li
          v-for="item in stats.recent_abnormals"
          :key="item.id"
          class="abnormal-item"
          @click="goRecord(item.id)"
        >
          <span class="abnormal-dot" />
          <div class="abnormal-body">
            <span class="abnormal-device">{{ item.device_code }} · {{ item.device_name }}</span>
            <span class="abnormal-desc">{{ item.remark || '点检异常' }}</span>
          </div>
          <div class="abnormal-meta">
            <span>{{ item.inspect_date }}</span>
            <span>{{ item.inspector }}</span>
          </div>
        </li>
      </ul>
      <div v-else class="abnormal-empty">暂无异常记录</div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { fetchInspectionDashboardStats } from '../../api/inspection'

use([CanvasRenderer, LineChart, BarChart, PieChart, GridComponent, TooltipComponent])

const router = useRouter()
const loading = ref(true)
const trendDays = ref(7)

const stats = reactive({
  today_due: 0,
  today_completed: 0,
  today_abnormal: 0,
  completion_rate: 0,
  trend: [],
  type_rates: [],
  recent_abnormals: [],
})

const todayLabel = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
})

function ringOption(percent, color) {
  return {
    series: [{
      type: 'pie',
      radius: ['72%', '88%'],
      center: ['50%', '50%'],
      silent: true,
      label: { show: false },
      data: [
        { value: percent, itemStyle: { color } },
        { value: 100 - percent, itemStyle: { color: 'rgba(255,255,255,0.06)' } },
      ],
    }],
  }
}

const dueRingOption = computed(() => ringOption(100, '#2b6cb0'))
const doneRingOption = computed(() => {
  const pct = stats.today_due ? Math.round(stats.today_completed / stats.today_due * 100) : 0
  return ringOption(pct, '#3182ce')
})
const abnormalRingOption = computed(() => {
  const pct = stats.today_completed
    ? Math.round(stats.today_abnormal / stats.today_completed * 100)
    : 0
  return ringOption(Math.min(pct, 100), '#e67e22')
})

const trendLineOption = computed(() => ({
  grid: { top: 24, right: 16, bottom: 28, left: 44 },
  tooltip: { trigger: 'axis', backgroundColor: 'rgba(13,17,23,0.92)', borderColor: '#2b6cb0' },
  xAxis: {
    type: 'category',
    data: stats.trend.map((p) => p.date.slice(5)),
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
    axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 11 },
  },
  yAxis: {
    type: 'value',
    max: 100,
    axisLabel: { color: 'rgba(255,255,255,0.5)', formatter: '{value}%' },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
  },
  series: [{
    type: 'line',
    data: stats.trend.map((p) => p.rate),
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    lineStyle: { color: '#3182ce', width: 2 },
    itemStyle: { color: '#3182ce' },
    areaStyle: {
      color: {
        type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: 'rgba(49,130,206,0.35)' },
          { offset: 1, color: 'rgba(49,130,206,0)' },
        ],
      },
    },
  }],
}))

const typeBarOption = computed(() => ({
  grid: { top: 8, right: 48, bottom: 8, left: 100 },
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, backgroundColor: 'rgba(13,17,23,0.92)' },
  xAxis: {
    type: 'value',
    max: 100,
    axisLabel: { color: 'rgba(255,255,255,0.5)', formatter: '{value}%' },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
  },
  yAxis: {
    type: 'category',
    data: stats.type_rates.map((t) => t.device_type),
    axisLabel: { color: 'rgba(255,255,255,0.65)', fontSize: 12 },
    axisLine: { show: false },
    axisTick: { show: false },
  },
  series: [{
    type: 'bar',
    data: stats.type_rates.map((t) => t.rate),
    barWidth: 14,
    itemStyle: {
      color: {
        type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
        colorStops: [
          { offset: 0, color: '#2b6cb0' },
          { offset: 1, color: '#4299e1' },
        ],
      },
      borderRadius: [0, 2, 2, 0],
    },
    label: {
      show: true,
      position: 'right',
      formatter: '{c}%',
      color: 'rgba(255,255,255,0.7)',
      fontSize: 11,
    },
  }],
}))

async function loadStats() {
  loading.value = true
  try {
    const data = await fetchInspectionDashboardStats(trendDays.value)
    Object.assign(stats, data)
  } finally {
    loading.value = false
  }
}

function switchTrend(days) {
  trendDays.value = days
  loadStats()
}

function goRecord(id) {
  router.push({ path: '/inspection/records', query: { detail: id } })
}

onMounted(loadStats)
</script>

<style scoped>
.inspection-dashboard {
  margin: -16px -20px;
  min-height: calc(100vh - 104px);
  background: #0d1117;
  padding: 24px 28px 32px;
  color: rgba(255, 255, 255, 0.85);
}

.dash-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(49, 130, 206, 0.25);
}

.header-badge {
  display: inline-block;
  font-size: 10px;
  letter-spacing: 2px;
  color: #4299e1;
  background: rgba(49, 130, 206, 0.15);
  padding: 2px 8px;
  margin-bottom: 8px;
}

.header-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #fff;
}

.header-date {
  margin-left: 16px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
}

.header-right {
  text-align: right;
}

.header-rate-label {
  display: block;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  margin-bottom: 4px;
}

.header-rate-value {
  font-size: 36px;
  font-weight: 700;
  color: #4299e1;
  font-variant-numeric: tabular-nums;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.kpi-panel {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.kpi-panel.kpi-abnormal {
  border-color: rgba(230, 126, 34, 0.3);
  background: rgba(230, 126, 34, 0.06);
}

.kpi-ring-wrap {
  position: relative;
  width: 100px;
  height: 100px;
  flex-shrink: 0;
}

.kpi-ring {
  width: 100%;
  height: 100%;
}

.kpi-ring-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.kpi-num {
  font-size: 32px;
  font-weight: 700;
  color: #fff;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.kpi-num.abnormal-num {
  color: #e67e22;
}

.kpi-unit {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  margin-top: 2px;
}

.kpi-label {
  font-size: 15px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
}

.kpi-label.abnormal-label {
  color: #e67e22;
}

.kpi-sub {
  display: block;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
  margin-top: 4px;
}

.chart-row {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.chart-panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 4px;
  padding: 16px 20px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.panel-title {
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
}

.panel-hint {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
}

.period-switch {
  display: flex;
  gap: 4px;
}

.period-switch button {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.55);
  font-size: 12px;
  padding: 4px 12px;
  cursor: pointer;
  border-radius: 2px;
}

.period-switch button.active {
  background: rgba(49, 130, 206, 0.25);
  border-color: #3182ce;
  color: #4299e1;
}

.trend-chart {
  height: 220px;
}

.type-chart {
  height: 220px;
}

.abnormal-section {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 4px;
  padding: 16px 20px;
}

.view-all {
  font-size: 12px;
  color: #4299e1;
  text-decoration: none;
}

.abnormal-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.abnormal-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  cursor: pointer;
  transition: background 0.15s;
}

.abnormal-item:hover {
  background: rgba(230, 126, 34, 0.08);
}

.abnormal-item:last-child {
  border-bottom: none;
}

.abnormal-dot {
  width: 8px;
  height: 8px;
  background: #e67e22;
  border-radius: 50%;
  flex-shrink: 0;
}

.abnormal-body {
  flex: 1;
  min-width: 0;
}

.abnormal-device {
  display: block;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.85);
}

.abnormal-desc {
  display: block;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.abnormal-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
  gap: 2px;
  flex-shrink: 0;
}

.abnormal-empty {
  text-align: center;
  padding: 32px;
  color: rgba(255, 255, 255, 0.3);
  font-size: 13px;
}
</style>
