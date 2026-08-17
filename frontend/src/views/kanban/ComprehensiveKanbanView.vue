<template>
  <div class="comprehensive-kanban">
    <!-- 顶部标题栏 -->
    <header class="kanban-header">
      <h1 class="kanban-title">综合看板</h1>
      <div class="header-right">
        <span class="refresh-hint">每 30s 自动刷新</span>
        <span class="datetime-text">{{ clockText }}</span>
      </div>
    </header>

    <!-- 五大模块网格 -->
    <div class="modules-grid">
      <!-- 模块一：生产进度 -->
      <section class="kanban-module module-production" v-loading="loading.production">
        <div class="module-header">
          <span class="module-icon">📊</span>
          <span class="module-title">生产进度</span>
        </div>
        <div class="module-body">
          <!-- 在制工单数 + 完成率环形 -->
          <div class="prod-top-row">
            <div class="prod-main-kpi">
              <div class="kpi-value">{{ data.production_progress?.active_orders ?? '-' }}</div>
              <div class="kpi-label">在制工单数</div>
            </div>
            <div class="prod-ring">
              <v-chart class="ring-chart" :option="completionRingOption" autoresize />
              <div class="ring-center-text">{{ data.production_progress?.completion_rate ?? 0 }}%</div>
            </div>
          </div>
          <!-- 排产达成率趋势 -->
          <div class="mini-chart-wrap">
            <div class="mini-title">排产达成率趋势</div>
            <v-chart class="mini-line-chart" :option="scheduleTrendOption" autoresize />
          </div>
          <!-- 产线状态条 -->
          <div class="line-status-wrap">
            <div class="mini-title">产线状态</div>
            <div class="line-status-list">
              <div
                v-for="line in data.production_progress?.line_status ?? []"
                :key="line.line_name"
                class="line-status-row"
              >
                <span class="line-name">{{ line.line_name }}</span>
                <div class="line-bar">
                  <div
                    class="bar-segment bar-in-production"
                    :style="{ flex: line.in_production }"
                    :title="`在制: ${line.in_production}`"
                  />
                  <div
                    class="bar-segment bar-completed"
                    :style="{ flex: line.completed }"
                    :title="`完成: ${line.completed}`"
                  />
                  <div
                    class="bar-segment bar-pending"
                    :style="{ flex: line.pending }"
                    :title="`待开工: ${line.pending}`"
                  />
                </div>
              </div>
            </div>
            <div class="line-legend">
              <span class="legend-dot dot-in-production"></span>在制
              <span class="legend-dot dot-completed"></span>完成
              <span class="legend-dot dot-pending"></span>待开工
            </div>
          </div>
        </div>
      </section>

      <!-- 模块二：品质概览 -->
      <section class="kanban-module module-quality" v-loading="loading.quality">
        <div class="module-header">
          <span class="module-icon">✅</span>
          <span class="module-title">品质概览</span>
        </div>
        <div class="module-body">
          <div class="quality-top-row">
            <div class="quality-kpi">
              <div class="kpi-value highlight-green">{{ data.quality_overview?.first_pass_rate ?? '-' }}%</div>
              <div class="kpi-label">直通率</div>
            </div>
          </div>
          <!-- 良率趋势 -->
          <div class="mini-chart-wrap">
            <div class="mini-title">良率趋势（近7天）</div>
            <v-chart class="mini-line-chart" :option="yieldTrendOption" autoresize />
          </div>
          <!-- 不良类型分布 -->
          <div class="mini-chart-wrap">
            <div class="mini-title">不良类型 Top5</div>
            <v-chart class="mini-bar-chart" :option="defectBarOption" autoresize />
          </div>
        </div>
      </section>

      <!-- 模块三：设备监控 -->
      <section class="kanban-module module-device" v-loading="loading.device">
        <div class="module-header">
          <span class="module-icon">🖥️</span>
          <span class="module-title">设备监控</span>
        </div>
        <div class="module-body">
          <!-- 稼动率卡片 -->
          <div class="device-cards">
            <div
              v-for="d in data.device_monitor?.devices ?? []"
              :key="d.code"
              class="device-card"
              :class="`device-${d.status}`"
            >
              <div class="device-ring-wrap">
                <v-chart class="device-ring-chart" :option="deviceRingOption(d)" autoresize />
                <span class="device-util-text">{{ d.utilization }}%</span>
              </div>
              <div class="device-name" :title="d.name">{{ d.name }}</div>
              <span class="device-status-tag" :class="`status-${d.status}`">{{ d.status }}</span>
            </div>
          </div>
          <!-- 状态分布饼图 + 预警 -->
          <div class="device-bottom-row">
            <div class="device-pie-wrap">
              <div class="mini-title">状态分布</div>
              <v-chart class="pie-chart" :option="deviceStatusPieOption" autoresize />
            </div>
            <div class="device-alert-wrap">
              <div class="mini-title">预警列表</div>
              <div class="alert-list">
                <div
                  v-for="alert in data.device_monitor?.alerts ?? []"
                  :key="alert.id"
                  class="alert-item"
                  :class="`severity-${alert.severity}`"
                >
                  <span class="alert-device">{{ alert.device_name }}</span>
                  <span class="alert-type">{{ alert.alert_type }}</span>
                  <span class="alert-time">{{ alert.time }}</span>
                </div>
                <div v-if="!(data.device_monitor?.alerts?.length)" class="alert-empty">暂无预警</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 模块四：订单交付 -->
      <section class="kanban-module module-order" v-loading="loading.order">
        <div class="module-header">
          <span class="module-icon">📦</span>
          <span class="module-title">订单交付</span>
        </div>
        <div class="module-body">
          <div class="order-kpi-row">
            <div class="order-kpi">
              <div class="kpi-value highlight-blue">{{ data.order_delivery?.delivery_rate ?? '-' }}%</div>
              <div class="kpi-label">交期达成率</div>
            </div>
            <div class="shipment-stats">
              <div class="shipment-item">
                <span class="shipment-num">{{ data.order_delivery?.shipment_stats?.this_week ?? '-' }}</span>
                <span class="shipment-label">本周出货</span>
              </div>
              <div class="shipment-item">
                <span class="shipment-num">{{ data.order_delivery?.shipment_stats?.this_month ?? '-' }}</span>
                <span class="shipment-label">本月出货</span>
              </div>
            </div>
          </div>
          <!-- 月度趋势 -->
          <div class="mini-chart-wrap">
            <div class="mini-title">月度交期趋势</div>
            <v-chart class="mini-bar-chart" :option="deliveryTrendOption" autoresize />
          </div>
          <!-- 逾期预警 -->
          <div class="overdue-wrap">
            <div class="mini-title">逾期预警</div>
            <div class="overdue-list">
              <div
                v-for="order in data.order_delivery?.overdue_orders ?? []"
                :key="order.order_no"
                class="overdue-item"
              >
                <span class="overdue-order-no">{{ order.order_no }}</span>
                <span class="overdue-customer">{{ order.customer }}</span>
                <span class="overdue-days">逾期{{ order.overdue_days }}天</span>
                <span class="overdue-status">{{ order.status }}</span>
              </div>
              <div v-if="!(data.order_delivery?.overdue_orders?.length)" class="alert-empty">暂无逾期订单</div>
            </div>
          </div>
        </div>
      </section>

      <!-- 模块五：物料库存 -->
      <section class="kanban-module module-material" v-loading="loading.material">
        <div class="module-header">
          <span class="module-icon">📋</span>
          <span class="module-title">物料库存</span>
        </div>
        <div class="module-body">
          <!-- 关键物料水位 -->
          <div class="material-list">
            <div
              v-for="m in data.material_inventory?.critical_materials ?? []"
              :key="m.name"
              class="material-row"
            >
              <div class="material-info">
                <span class="material-name">{{ m.name }}</span>
                <span class="material-stock">{{ m.current_stock }} / {{ m.max_stock }}</span>
              </div>
              <div class="material-bar-wrap">
                <div class="material-bar-bg">
                  <div
                    class="material-bar-fill"
                    :class="`fill-${m.status}`"
                    :style="{ width: materialPercent(m) + '%' }"
                  />
                  <div
                    class="material-safety-line"
                    :style="{ left: materialSafetyPercent(m) + '%' }"
                    title="安全线"
                  />
                </div>
              </div>
            </div>
          </div>
          <!-- 短缺预警 -->
          <div v-if="data.material_inventory?.shortage_alerts?.length" class="shortage-wrap">
            <div class="mini-title shortage-title">⚠️ 短缺预警</div>
            <div class="shortage-list">
              <div
                v-for="(alert, idx) in data.material_inventory?.shortage_alerts ?? []"
                :key="idx"
                class="shortage-item"
              >
                {{ alert }}
              </div>
            </div>
          </div>
          <!-- 周转天数趋势 -->
          <div class="mini-chart-wrap">
            <div class="mini-title">周转天数趋势</div>
            <v-chart class="mini-line-chart" :option="turnoverTrendOption" autoresize />
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, GaugeChart, LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { fetchComprehensiveKanban } from '../../api/kanbanGeneral'

use([
  CanvasRenderer,
  BarChart,
  GaugeChart,
  LineChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
])

const REFRESH_INTERVAL = 30000

const data = reactive({
  production_progress: null,
  quality_overview: null,
  device_monitor: null,
  order_delivery: null,
  material_inventory: null,
})

const loading = reactive({
  production: true,
  quality: true,
  device: true,
  order: true,
  material: true,
})

const clockText = ref('')
let clockTimer = null
let refreshTimer = null

function updateClock() {
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  clockText.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}

// ---- 暗色图表通用配置 ----
const darkTooltip = {
  backgroundColor: 'rgba(10, 26, 58, 0.95)',
  borderColor: 'rgba(64, 224, 208, 0.3)',
  textStyle: { color: '#fff', fontSize: 12 },
}

const darkAxisLine = { lineStyle: { color: 'rgba(255,255,255,0.12)' } }
const darkSplitLine = { lineStyle: { color: 'rgba(255,255,255,0.06)' } }
const darkAxisLabel = { color: 'rgba(255,255,255,0.5)', fontSize: 10 }

// ---- 模块一：完成率环形 ----
const completionRingOption = computed(() => ({
  series: [{
    type: 'pie',
    radius: ['62%', '82%'],
    center: ['50%', '50%'],
    silent: true,
    label: { show: false },
    emphasis: { disabled: true },
    data: [
      { value: data.production_progress?.completion_rate ?? 0, itemStyle: { color: '#40e0d0' } },
      { value: 100 - (data.production_progress?.completion_rate ?? 0), itemStyle: { color: 'rgba(255,255,255,0.08)' } },
    ],
  }],
}))

// ---- 模块一：排产达成率趋势 ----
const scheduleTrendOption = computed(() => {
  const points = data.production_progress?.schedule_achievement_trend ?? []
  return {
    tooltip: { ...darkTooltip, trigger: 'axis' },
    grid: { left: 36, right: 12, top: 8, bottom: 20 },
    xAxis: {
      type: 'category',
      data: points.map(p => p.label),
      axisLine: darkAxisLine,
      axisLabel: darkAxisLabel,
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 70,
      max: 100,
      axisLine: { show: false },
      axisLabel: { ...darkAxisLabel, formatter: '{value}%' },
      splitLine: darkSplitLine,
    },
    series: [{
      type: 'line',
      data: points.map(p => p.value),
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { color: '#40e0d0', width: 2 },
      itemStyle: { color: '#40e0d0' },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(64,224,208,0.25)' },
            { offset: 1, color: 'rgba(64,224,208,0.02)' },
          ],
        },
      },
    }],
  }
})

// ---- 模块二：良率趋势 ----
const yieldTrendOption = computed(() => {
  const points = data.quality_overview?.yield_trend ?? []
  const target = data.quality_overview?.yield_target ?? 95
  return {
    tooltip: { ...darkTooltip, trigger: 'axis' },
    grid: { left: 36, right: 12, top: 8, bottom: 20 },
    xAxis: {
      type: 'category',
      data: points.map(p => p.label),
      axisLine: darkAxisLine,
      axisLabel: darkAxisLabel,
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 90,
      max: 100,
      axisLine: { show: false },
      axisLabel: { ...darkAxisLabel, formatter: '{value}%' },
      splitLine: darkSplitLine,
    },
    series: [
      {
        type: 'line',
        data: points.map(p => p.value),
        name: '良率',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: '#52c41a', width: 2 },
        itemStyle: { color: '#52c41a' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(82,196,26,0.22)' },
              { offset: 1, color: 'rgba(82,196,26,0.02)' },
            ],
          },
        },
      },
      {
        type: 'line',
        data: points.map(() => target),
        name: '目标线',
        symbol: 'none',
        lineStyle: { color: '#faad14', type: 'dashed', width: 1.5 },
        silent: true,
      },
    ],
  }
})

// ---- 模块二：不良类型分布横向条形图 ----
const defectBarOption = computed(() => {
  const items = [...(data.quality_overview?.defect_distribution ?? [])].reverse()
  const maxVal = Math.max(...items.map(i => i.value), 1)
  return {
    tooltip: { ...darkTooltip, trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 36, right: 20, top: 4, bottom: 20 },
    xAxis: {
      type: 'value',
      max: maxVal * 1.3,
      axisLine: { show: false },
      axisLabel: { ...darkAxisLabel },
      splitLine: darkSplitLine,
    },
    yAxis: {
      type: 'category',
      data: items.map(i => i.name),
      axisLine: { show: false },
      axisLabel: { ...darkAxisLabel, fontSize: 10 },
      axisTick: { show: false },
    },
    series: [{
      type: 'bar',
      barWidth: 10,
      data: items.map(i => ({
        value: i.value,
        itemStyle: {
          borderRadius: [0, 4, 4, 0],
          color: {
            type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: '#fa8c16' },
              { offset: 1, color: '#ff4d4f' },
            ],
          },
        },
      })),
      label: {
        show: true,
        position: 'right',
        color: 'rgba(255,255,255,0.65)',
        fontSize: 10,
      },
    }],
  }
})

// ---- 模块三：设备稼动率环形 ----
function deviceRingOption(device) {
  const val = device.utilization ?? 0
  const colorMap = {
    '运行': '#52c41a',
    '待机': '#faad14',
    '维修': '#fa8c16',
    '停机': '#ff4d4f',
  }
  const color = colorMap[device.status] || '#999'
  return {
    series: [{
      type: 'pie',
      radius: ['60%', '78%'],
      center: ['50%', '50%'],
      silent: true,
      label: { show: false },
      emphasis: { disabled: true },
      data: [
        { value: val, itemStyle: { color } },
        { value: 100 - val, itemStyle: { color: 'rgba(255,255,255,0.06)' } },
      ],
    }],
  }
}

// ---- 模块三：设备状态分布饼图 ----
const deviceStatusPieOption = computed(() => {
  const items = data.device_monitor?.status_distribution ?? []
  return {
    tooltip: { ...darkTooltip, trigger: 'item', formatter: '{b}: {c}台 ({d}%)' },
    legend: {
      bottom: 0,
      textStyle: { color: 'rgba(255,255,255,0.55)', fontSize: 10 },
      itemWidth: 10,
      itemHeight: 6,
    },
    series: [{
      type: 'pie',
      radius: ['45%', '72%'],
      center: ['50%', '44%'],
      label: { show: false },
      emphasis: { disabled: true },
      data: items.map(i => ({
        name: i.name,
        value: i.value,
        itemStyle: { color: i.color },
      })),
    }],
  }
})

// ---- 模块四：月度交期趋势 ----
const deliveryTrendOption = computed(() => {
  const points = data.order_delivery?.monthly_trend ?? []
  return {
    tooltip: { ...darkTooltip, trigger: 'axis' },
    grid: { left: 36, right: 12, top: 8, bottom: 20 },
    xAxis: {
      type: 'category',
      data: points.map(p => p.label),
      axisLine: darkAxisLine,
      axisLabel: darkAxisLabel,
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 80,
      max: 100,
      axisLine: { show: false },
      axisLabel: { ...darkAxisLabel, formatter: '{value}%' },
      splitLine: darkSplitLine,
    },
    series: [{
      type: 'bar',
      barWidth: 14,
      data: points.map(p => ({
        value: p.value,
        itemStyle: {
          borderRadius: [3, 3, 0, 0],
          color: {
            type: 'linear', x: 0, y: 1, x2: 0, y2: 0,
            colorStops: [
              { offset: 0, color: '#1e3a8a' },
              { offset: 1, color: '#3b82f6' },
            ],
          },
        },
      })),
    }],
  }
})

// ---- 模块五：周转天数趋势 ----
const turnoverTrendOption = computed(() => {
  const points = data.material_inventory?.turnover_days_trend ?? []
  return {
    tooltip: { ...darkTooltip, trigger: 'axis' },
    grid: { left: 36, right: 12, top: 8, bottom: 20 },
    xAxis: {
      type: 'category',
      data: points.map(p => p.label),
      axisLine: darkAxisLine,
      axisLabel: darkAxisLabel,
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { ...darkAxisLabel, formatter: '{value}天' },
      splitLine: darkSplitLine,
    },
    series: [{
      type: 'line',
      data: points.map(p => p.value),
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { color: '#fa8c16', width: 2 },
      itemStyle: { color: '#fa8c16' },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(250,140,22,0.2)' },
            { offset: 1, color: 'rgba(250,140,22,0.02)' },
          ],
        },
      },
    }],
  }
})

// ---- 物料百分比计算 ----
function materialPercent(m) {
  if (!m || m.max_stock <= 0) return 0
  return Math.min((m.current_stock / m.max_stock) * 100, 100)
}

function materialSafetyPercent(m) {
  if (!m || m.max_stock <= 0) return 0
  return (m.safety_line / m.max_stock) * 100
}

// ---- 数据加载 ----
async function loadAll() {
  try {
    const resp = await fetchComprehensiveKanban()
    if (resp.production_progress) {
      data.production_progress = resp.production_progress
      loading.production = false
    }
    if (resp.quality_overview) {
      data.quality_overview = resp.quality_overview
      loading.quality = false
    }
    if (resp.device_monitor) {
      data.device_monitor = resp.device_monitor
      loading.device = false
    }
    if (resp.order_delivery) {
      data.order_delivery = resp.order_delivery
      loading.order = false
    }
    if (resp.material_inventory) {
      data.material_inventory = resp.material_inventory
      loading.material = false
    }
  } catch {
    // 保持旧数据，仅标记加载完成
    loading.production = false
    loading.quality = false
    loading.device = false
    loading.order = false
    loading.material = false
  }
}

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
  loadAll()
  refreshTimer = setInterval(loadAll, REFRESH_INTERVAL)
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
/* ===== 页面容器 ===== */
.comprehensive-kanban {
  margin: -16px -20px;
  width: calc(100% + 40px);
  max-width: calc(100% + 40px);
  min-width: 0;
  min-height: calc(100vh - 120px);
  padding: 12px 16px 20px;
  background: #040a1a;
  color: #fff;
  box-sizing: border-box;
  overflow-x: hidden;
}

/* ===== 顶部标题 ===== */
.kanban-header {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-bottom: 14px;
  padding: 4px 0 10px;
  border-bottom: 1px solid rgba(64, 224, 208, 0.1);
}

.kanban-title {
  margin: 0;
  font-size: 26px;
  font-weight: 600;
  color: #fff;
  letter-spacing: 4px;
}

.header-right {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.refresh-hint {
  font-size: 11px;
  color: rgba(64, 224, 208, 0.5);
}

.datetime-text {
  font-size: 13px;
  color: #40e0d0;
  font-family: 'Courier New', monospace;
}

/* ===== 五大模块网格 ===== */
.modules-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
  max-width: 100%;
}

/* 生产进度占 2/3 宽 */
.module-production {
  grid-column: span 2;
}

/* ===== 模块卡片 ===== */
.kanban-module {
  background: #0a1a3a;
  border-radius: 8px;
  border: 1px solid rgba(64, 224, 208, 0.12);
  display: flex;
  flex-direction: column;
  min-height: 360px;
  min-width: 0;
  overflow: hidden;
}

.module-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(64, 224, 208, 0.1);
}

.module-icon {
  font-size: 16px;
}

.module-title {
  font-size: 14px;
  font-weight: 600;
  color: #40e0d0;
  letter-spacing: 1px;
}

.module-body {
  flex: 1;
  padding: 10px 14px 14px;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ===== 通用 KPI 数字 ===== */
.kpi-value {
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
}

.kpi-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
  margin-top: 2px;
}

.highlight-green { color: #52c41a; text-shadow: 0 0 12px rgba(82, 196, 26, 0.4); }
.highlight-blue { color: #40e0d0; text-shadow: 0 0 12px rgba(64, 224, 208, 0.4); }

/* ===== 生产进度 ===== */
.prod-top-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.prod-main-kpi {
  flex-shrink: 0;
}

.prod-main-kpi .kpi-value {
  font-size: 40px;
  color: #f5a623;
  text-shadow: 0 0 16px rgba(245, 166, 35, 0.4);
}

.prod-ring {
  position: relative;
  width: 90px;
  height: 90px;
  flex-shrink: 0;
}

.ring-chart {
  width: 100%;
  height: 100%;
}

.ring-center-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 15px;
  font-weight: 700;
  color: #40e0d0;
}

/* 迷你图表 */
.mini-chart-wrap {
  min-height: 0;
}

.mini-title {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 2px;
  letter-spacing: 0.5px;
}

.mini-line-chart {
  width: 100%;
  height: 90px;
}

.mini-bar-chart {
  width: 100%;
  height: 100px;
}

/* 产线状态 */
.line-status-wrap {
  margin-top: 2px;
}

.line-status-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.line-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.line-name {
  width: 64px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.65);
  flex-shrink: 0;
  text-align: right;
}

.line-bar {
  flex: 1;
  display: flex;
  height: 14px;
  border-radius: 3px;
  overflow: hidden;
}

.bar-segment {
  transition: flex 0.3s;
}

.bar-in-production { background: #3b82f6; }
.bar-completed { background: #52c41a; }
.bar-pending { background: rgba(255, 255, 255, 0.12); }

.line-legend {
  display: flex;
  align-items: center;
  gap: 4px 12px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.45);
  margin-top: 6px;
  flex-wrap: wrap;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  display: inline-block;
}

.dot-in-production { background: #3b82f6; }
.dot-completed { background: #52c41a; }
.dot-pending { background: rgba(255, 255, 255, 0.12); }

/* ===== 品质概览 ===== */
.quality-top-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.quality-kpi .kpi-value {
  font-size: 34px;
}

/* ===== 设备监控 ===== */
.device-cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.device-card {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  padding: 8px 6px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  border: 1px solid transparent;
  min-width: 0;
}

.device-card.device-运行 { border-color: rgba(82, 196, 26, 0.2); }
.device-card.device-待机 { border-color: rgba(250, 173, 20, 0.2); }
.device-card.device-维修 { border-color: rgba(250, 140, 22, 0.2); }
.device-card.device-停机 { border-color: rgba(255, 77, 79, 0.2); }

.device-ring-wrap {
  position: relative;
  width: 52px;
  height: 52px;
  flex-shrink: 0;
}

.device-ring-chart {
  width: 100%;
  height: 100%;
}

.device-util-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 10px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.85);
}

.device-name {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.device-status-tag {
  font-size: 9px;
  padding: 1px 6px;
  border-radius: 2px;
  font-weight: 500;
}

.status-运行 { background: rgba(82, 196, 26, 0.2); color: #52c41a; }
.status-待机 { background: rgba(250, 173, 20, 0.2); color: #faad14; }
.status-维修 { background: rgba(250, 140, 22, 0.2); color: #fa8c16; }
.status-停机 { background: rgba(255, 77, 79, 0.2); color: #ff4d4f; }

/* 设备底部：饼图+预警 */
.device-bottom-row {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.device-pie-wrap {
  flex: 1;
  min-width: 0;
}

.device-pie-wrap .mini-title,
.device-alert-wrap .mini-title {
  margin-bottom: 2px;
}

.pie-chart {
  width: 100%;
  height: 100px;
}

.device-alert-wrap {
  flex: 1;
  min-width: 0;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  border-radius: 3px;
  font-size: 10px;
  background: rgba(255, 255, 255, 0.03);
  border-left: 3px solid;
}

.alert-item.severity-urgent { border-color: #ff4d4f; background: rgba(255, 77, 79, 0.08); }
.alert-item.severity-high { border-color: #fa8c16; background: rgba(250, 140, 22, 0.06); }
.alert-item.severity-normal { border-color: #faad14; background: rgba(250, 173, 20, 0.05); }

.alert-device { flex: 1; color: rgba(255,255,255,0.8); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.alert-type { color: rgba(255,255,255,0.5); flex-shrink: 0; }
.alert-time { color: rgba(255,255,255,0.35); flex-shrink: 0; }

.alert-empty {
  font-size: 10px;
  color: rgba(255,255,255,0.3);
  text-align: center;
  padding: 12px 0;
}

/* ===== 订单交付 ===== */
.order-kpi-row {
  display: flex;
  align-items: center;
  gap: 20px;
}

.order-kpi .kpi-value {
  font-size: 34px;
}

.shipment-stats {
  display: flex;
  gap: 16px;
}

.shipment-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.shipment-num {
  font-size: 18px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
}

.shipment-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.45);
}

/* 逾期预警 */
.overdue-wrap {
  margin-top: 4px;
}

.overdue-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.overdue-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  border-radius: 3px;
  font-size: 11px;
  background: rgba(255, 77, 79, 0.06);
  border-left: 3px solid #ff4d4f;
}

.overdue-order-no { color: rgba(255,255,255,0.8); font-weight: 500; }
.overdue-customer { color: rgba(255,255,255,0.55); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.overdue-days { color: #ff4d4f; font-weight: 600; }
.overdue-status { color: rgba(255,255,255,0.4); font-size: 10px; padding: 1px 5px; background: rgba(255,255,255,0.06); border-radius: 2px; }

/* ===== 物料库存 ===== */
.material-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.material-row {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.material-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.material-name {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.75);
}

.material-stock {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
}

.material-bar-wrap {
  width: 100%;
}

.material-bar-bg {
  position: relative;
  width: 100%;
  height: 12px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  overflow: visible;
}

.material-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s;
  min-width: 2px;
}

.fill-normal { background: #52c41a; }
.fill-warning { background: #faad14; }
.fill-shortage { background: #ff4d4f; box-shadow: 0 0 6px rgba(255, 77, 79, 0.5); }

.material-safety-line {
  position: absolute;
  top: -2px;
  bottom: -2px;
  width: 2px;
  background: rgba(255, 255, 255, 0.35);
  border-radius: 1px;
}

/* 短缺预警 */
.shortage-wrap {
  margin-top: 2px;
}

.shortage-title {
  color: #ff4d4f !important;
}

.shortage-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.shortage-item {
  font-size: 10px;
  color: #ff7875;
  padding: 3px 6px;
  background: rgba(255, 77, 79, 0.08);
  border-radius: 2px;
  border-left: 2px solid #ff4d4f;
}

/* ===== loading 暗色适配 ===== */
:deep(.el-loading-mask) {
  background: rgba(4, 10, 26, 0.7);
}

:deep(.el-loading-spinner .path) {
  stroke: #40e0d0;
}

/* ===== 响应式 ===== */
@media (max-width: 1200px) {
  .modules-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .module-production {
    grid-column: span 2;
  }

  .device-cards {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .modules-grid {
    grid-template-columns: 1fr;
  }

  .module-production {
    grid-column: span 1;
  }

  .device-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .device-bottom-row {
    flex-direction: column;
  }

  .kanban-title {
    font-size: 20px;
  }
}
</style>
