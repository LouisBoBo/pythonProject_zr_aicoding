<template>
  <div v-loading="loading" class="equipment-oee-kanban">
    <header class="kanban-header">
      <h1 class="kanban-title">设备 OEE 看板</h1>
      <div class="header-tools">
        <el-radio-group v-model="period" size="small" class="period-group" @change="loadKanban">
          <el-radio-button value="day">今日</el-radio-button>
          <el-radio-button value="week">本周</el-radio-button>
          <el-radio-button value="month">本月</el-radio-button>
        </el-radio-group>
        <div class="kanban-datetime">
          <span class="datetime-text">{{ displayTime }}</span>
          <span class="weekday-text">{{ weekday }}</span>
        </div>
      </div>
    </header>

    <section class="kpi-row">
      <div
        v-for="card in kpiCards"
        :key="card.key"
        class="kanban-card kpi-card"
        :class="{ highlight: card.highlight }"
      >
        <div class="kpi-label">{{ card.label }}</div>
        <div class="kpi-value">{{ card.value }}<span class="kpi-unit">%</span></div>
      </div>
    </section>

    <div class="kanban-grid">
      <div class="kanban-card table-card ranking-card">
        <div class="card-title">设备 OEE 排行</div>
        <div class="table-wrap">
          <el-table :data="ranking" class="dark-table" stripe :show-header="true" max-height="420">
            <el-table-column prop="rank" label="排名" width="64" align="center" />
            <el-table-column prop="equipment_code" label="设备编号" min-width="110" />
            <el-table-column prop="equipment_name" label="设备名称" min-width="120" />
            <el-table-column prop="workshop" label="车间" min-width="90">
              <template #default="{ row }">{{ row.workshop || '—' }}</template>
            </el-table-column>
            <el-table-column prop="oee" label="OEE" min-width="72" align="right">
              <template #default="{ row }">{{ formatPct(row.oee) }}</template>
            </el-table-column>
            <el-table-column prop="availability" label="时间稼动率" min-width="100" align="right">
              <template #default="{ row }">{{ formatPct(row.availability) }}</template>
            </el-table-column>
            <el-table-column prop="performance" label="性能稼动率" min-width="100" align="right">
              <template #default="{ row }">{{ formatPct(row.performance) }}</template>
            </el-table-column>
            <el-table-column prop="quality" label="良品率" min-width="80" align="right">
              <template #default="{ row }">{{ formatPct(row.quality) }}</template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <div class="kanban-col-right">
        <div class="kanban-card chart-card">
          <div class="card-title">设备 OEE Top 10</div>
          <div class="chart-wrap">
            <v-chart class="bar-chart" :option="rankBarOption" autoresize />
          </div>
        </div>
        <div class="kanban-card chart-card trend-card">
          <div class="card-title-row">
            <span class="card-title inline">近 {{ trendDays }} 天 OEE 趋势</span>
            <el-radio-group v-model="trendDays" size="small" class="trend-days" @change="loadTrend">
              <el-radio-button :value="7">7天</el-radio-button>
              <el-radio-button :value="14">14天</el-radio-button>
              <el-radio-button :value="30">30天</el-radio-button>
            </el-radio-group>
          </div>
          <div class="chart-wrap">
            <v-chart v-if="trend.length" class="line-chart" :option="trendLineOption" autoresize />
            <div v-else class="chart-empty">暂无趋势数据</div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loadError" class="load-error">{{ loadError }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { fetchEquipmentOeeKanban } from '../../api/kanbanEquipmentOee.js'
import { fetchEquipmentOeeReport } from '../../api/reports/equipmentOee.js'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(true)
const loadError = ref('')
const period = ref('day')
const trendDays = ref(7)
const displayTime = ref('')
const weekday = ref('')

const summary = reactive({
  availability: 0,
  performance: 0,
  quality: 0,
  oee: 0,
})

const ranking = ref([])
const rankChart = reactive({ labels: [], values: [] })
const trend = ref([])

const kpiCards = computed(() => [
  { key: 'availability', label: '时间稼动率', value: formatPct(summary.availability) },
  { key: 'performance', label: '性能稼动率', value: formatPct(summary.performance) },
  { key: 'quality', label: '良品率', value: formatPct(summary.quality) },
  { key: 'oee', label: 'OEE 综合', value: formatPct(summary.oee), highlight: true },
])

const rankBarOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(10, 26, 58, 0.95)',
    borderColor: 'rgba(64, 224, 208, 0.3)',
    textStyle: { color: '#fff' },
    valueFormatter: (v) => `${Number(v).toFixed(2)}%`,
  },
  grid: { left: 48, right: 20, top: 24, bottom: 56 },
  xAxis: {
    type: 'category',
    data: rankChart.labels,
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
    axisLabel: {
      color: 'rgba(255,255,255,0.6)',
      fontSize: 11,
      rotate: rankChart.labels.length > 6 ? 28 : 0,
      interval: 0,
    },
    axisTick: { show: false },
  },
  yAxis: {
    type: 'value',
    min: 0,
    max: 100,
    axisLine: { show: false },
    axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 11 },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
  },
  series: [
    {
      name: 'OEE',
      type: 'bar',
      barWidth: 22,
      data: rankChart.values,
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: {
          type: 'linear',
          x: 0,
          y: 1,
          x2: 0,
          y2: 0,
          colorStops: [
            { offset: 0, color: '#1e3a8a' },
            { offset: 1, color: '#40e0d0' },
          ],
        },
      },
    },
  ],
}))

const trendLineOption = computed(() => {
  const dates = trend.value.map((p) => p.period_date)
  const seriesDefs = [
    { name: 'OEE', key: 'oee', color: '#40e0d0' },
    { name: '时间稼动率', key: 'availability', color: '#67C23A' },
    { name: '性能稼动率', key: 'performance', color: '#E6A23C' },
    { name: '良品率', key: 'quality', color: '#F56C6C' },
  ]
  return {
    color: seriesDefs.map((s) => s.color),
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(10, 26, 58, 0.95)',
      borderColor: 'rgba(64, 224, 208, 0.3)',
      textStyle: { color: '#fff' },
    },
    legend: {
      data: seriesDefs.map((s) => s.name),
      bottom: 0,
      textStyle: { color: 'rgba(255,255,255,0.75)', fontSize: 11 },
    },
    grid: { left: 48, right: 20, top: 28, bottom: 48 },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      name: '%',
      nameTextStyle: { color: 'rgba(255,255,255,0.5)' },
      axisLine: { show: false },
      axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
    },
    series: seriesDefs.map((s) => ({
      name: s.name,
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: trend.value.map((p) => p[s.key]),
    })),
  }
})

function formatPct(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
}

function formatDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function trendDateRange(days) {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - (days - 1))
  return [formatDate(start), formatDate(end)]
}

function applyKanban(resp) {
  const s = resp?.summary || {}
  summary.availability = s.availability ?? 0
  summary.performance = s.performance ?? 0
  summary.quality = s.quality ?? 0
  summary.oee = s.oee ?? 0
  ranking.value = resp?.ranking || []
  const chart = resp?.chart || {}
  rankChart.labels = chart.labels || []
  rankChart.values = chart.values || []
}

let clockTimer = null

function updateClock() {
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
  displayTime.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
  weekday.value = weekdays[now.getDay()]
}

async function loadTrend() {
  const [dateFrom, dateTo] = trendDateRange(trendDays.value)
  try {
    const resp = await fetchEquipmentOeeReport({
      page: 1,
      pageSize: 1,
      dateFrom,
      dateTo,
    })
    trend.value = resp?.trend || []
  } catch {
    trend.value = []
  }
}

async function loadKanban() {
  loadError.value = ''
  try {
    const resp = await fetchEquipmentOeeKanban({ period: period.value, limit: 30 })
    applyKanban(resp)
  } catch (err) {
    loadError.value = err.message || '加载看板数据失败'
    applyKanban(null)
  }
}

async function loadAll() {
  loading.value = true
  await Promise.all([loadKanban(), loadTrend()])
  loading.value = false
}

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
  loadAll()
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
})
</script>

<style scoped>
.equipment-oee-kanban {
  margin: -16px -20px;
  width: calc(100% + 40px);
  max-width: calc(100% + 40px);
  min-width: 0;
  min-height: calc(100vh - 120px);
  padding: 12px 16px 16px;
  background: #040a1a;
  color: #fff;
  box-sizing: border-box;
  overflow-x: hidden;
}

.kanban-header {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-bottom: 12px;
  padding: 4px 0 8px;
}

.kanban-title {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  color: #fff;
  letter-spacing: 4px;
}

.header-tools {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  gap: 16px;
}

.period-group :deep(.el-radio-button__inner) {
  background: rgba(10, 26, 58, 0.9);
  border-color: rgba(64, 224, 208, 0.25);
  color: rgba(255, 255, 255, 0.75);
}

.period-group :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: rgba(64, 224, 208, 0.2);
  border-color: #40e0d0;
  color: #40e0d0;
  box-shadow: none;
}

.kanban-datetime {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.datetime-text {
  font-size: 14px;
  color: #40e0d0;
  font-family: 'Courier New', monospace;
}

.weekday-text {
  font-size: 13px;
  color: rgba(64, 224, 208, 0.75);
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.kanban-card {
  border-radius: 8px;
  border: 1px solid rgba(64, 224, 208, 0.12);
  overflow: hidden;
  min-width: 0;
}

.kpi-card {
  background: linear-gradient(
    180deg,
    rgba(10, 40, 80, 0.9) 0%,
    rgba(10, 26, 58, 0.95) 100%
  );
  padding: 14px 16px;
  text-align: center;
}

.kpi-card.highlight {
  border-color: rgba(245, 166, 35, 0.35);
  background: linear-gradient(
    180deg,
    rgba(245, 166, 35, 0.25) 0%,
    rgba(10, 26, 58, 0.95) 55%
  );
}

.kpi-label {
  font-size: 14px;
  color: #40e0d0;
  letter-spacing: 1px;
  margin-bottom: 8px;
}

.kpi-value {
  font-size: 32px;
  font-weight: 700;
  color: #f5a623;
  line-height: 1.1;
}

.kpi-card.highlight .kpi-value {
  font-size: 36px;
  text-shadow: 0 0 12px rgba(245, 166, 35, 0.35);
}

.kpi-unit {
  font-size: 16px;
  font-weight: 500;
  margin-left: 2px;
  color: rgba(255, 255, 255, 0.65);
}

.kanban-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 12px;
  min-height: 480px;
}

.kanban-col-right {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.card-title {
  text-align: center;
  font-size: 15px;
  font-weight: 500;
  color: #40e0d0;
  padding: 10px 12px 6px;
  letter-spacing: 1px;
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px 4px;
  gap: 8px;
}

.card-title.inline {
  padding: 0;
  text-align: left;
}

.trend-days :deep(.el-radio-button__inner) {
  background: rgba(10, 26, 58, 0.9);
  border-color: rgba(64, 224, 208, 0.2);
  color: rgba(255, 255, 255, 0.7);
  padding: 5px 10px;
}

.trend-days :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: rgba(64, 224, 208, 0.15);
  border-color: #40e0d0;
  color: #40e0d0;
}

.table-card,
.chart-card {
  background: #0a1a3a;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.ranking-card {
  flex: 1;
}

.trend-card {
  flex: 1;
  min-height: 220px;
}

.table-wrap {
  flex: 1;
  min-width: 0;
  overflow: auto;
  padding: 0 8px 8px;
}

.chart-wrap {
  flex: 1;
  min-height: 200px;
  padding: 0 8px 12px;
}

.bar-chart,
.line-chart {
  width: 100%;
  height: 100%;
  min-height: 200px;
}

.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 180px;
  color: rgba(255, 255, 255, 0.45);
  font-size: 14px;
}

.dark-table {
  width: max-content;
  min-width: 100%;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(10, 40, 80, 0.8);
  --el-table-row-hover-bg-color: rgba(64, 224, 208, 0.06);
  --el-table-border-color: transparent;
  --el-table-text-color: rgba(255, 255, 255, 0.85);
  --el-table-header-text-color: #40e0d0;
  background: transparent !important;
}

.dark-table :deep(.el-table__inner-wrapper)::before {
  display: none;
}

.dark-table :deep(th.el-table__cell) {
  background: rgba(10, 40, 80, 0.8) !important;
  color: #40e0d0 !important;
  font-weight: 500;
  font-size: 13px;
  border-bottom: 1px solid rgba(64, 224, 208, 0.15) !important;
}

.dark-table :deep(td.el-table__cell) {
  background: transparent !important;
  color: rgba(255, 255, 255, 0.82) !important;
  font-size: 13px;
  border-bottom: none !important;
}

.dark-table :deep(.el-table__row--striped td.el-table__cell) {
  background: rgba(255, 255, 255, 0.02) !important;
}

.load-error {
  text-align: center;
  color: #f56c6c;
  padding: 12px;
  font-size: 14px;
}

@media (max-width: 1100px) {
  .kpi-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .kanban-grid {
    grid-template-columns: 1fr;
  }
}
</style>
