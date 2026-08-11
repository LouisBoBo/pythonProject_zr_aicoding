<template>
  <div v-loading="loading" class="quality-dashboard">
    <header class="qd-header">
      <div class="header-main">
        <span class="header-badge">QUALITY</span>
        <h1 class="header-title">品质监控看板</h1>
        <span class="header-sub">一屏掌握品质全貌 · 快速定位异常</span>
      </div>
      <div class="header-actions">
        <el-radio-group v-model="kpiPeriod" size="small" @change="loadKpi">
          <el-radio-button value="day">今日</el-radio-button>
          <el-radio-button value="week">本周</el-radio-button>
          <el-radio-button value="month">本月</el-radio-button>
        </el-radio-group>
        <span class="header-time">{{ nowLabel }}</span>
      </div>
    </header>

    <section class="screen-primary">
      <QualityKpiCards :items="kpiItems" />

      <div class="alert-panel">
        <div class="panel-head">
          <span class="panel-title">
            <span class="alert-dot" />
            品质异常实时预警
          </span>
          <span class="alert-count">{{ anomalies.length }} 条未处理</span>
        </div>
        <el-table
          :data="anomalies"
          class="alert-table"
          :show-header="true"
          size="small"
          max-height="220"
        >
          <el-table-column prop="discovered_at" label="时间" min-width="110">
            <template #default="{ row }">
              {{ formatTime(row.discovered_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="production_line" label="产线" min-width="90" />
          <el-table-column prop="defect_type" label="缺陷类型" min-width="90" />
          <el-table-column prop="process" label="工序" min-width="80" />
          <el-table-column prop="severity" label="严重程度" min-width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="severityTagType(row.severity)" size="small" effect="dark">
                {{ severityLabel(row.severity) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <section class="screen-analysis">
      <div class="chart-panel trend-panel">
        <div class="panel-head">
          <span class="panel-title">品质趋势</span>
          <el-radio-group v-model="trendGranularity" size="small" @change="loadTrend">
            <el-radio-button value="day">日</el-radio-button>
            <el-radio-button value="week">周</el-radio-button>
            <el-radio-button value="month">月</el-radio-button>
          </el-radio-group>
        </div>
        <v-chart class="chart-box trend-chart" :option="trendOption" autoresize />
      </div>

      <div class="chart-panel process-panel">
        <div class="panel-head">
          <span class="panel-title">各工序一次合格率</span>
          <span class="panel-hint">近7天</span>
        </div>
        <v-chart class="chart-box process-chart" :option="processBarOption" autoresize />
      </div>
    </section>

    <section class="screen-detail">
      <div class="detail-left">
        <div class="chart-panel">
          <div class="panel-head">
            <span class="panel-title">缺陷类型分布</span>
          </div>
          <v-chart class="chart-box donut-chart" :option="defectTypeOption" autoresize />
        </div>
        <div class="chart-panel">
          <div class="panel-head">
            <span class="panel-title">产线缺陷分布</span>
          </div>
          <v-chart class="chart-box bar-chart" :option="defectLineOption" autoresize />
        </div>
      </div>

      <div class="detail-right">
        <div class="chart-panel table-panel">
          <div class="panel-head">
            <span class="panel-title">Top 10 不良品/缺陷排行</span>
          </div>
          <el-table :data="topDefects" class="rank-table" size="small" stripe>
            <el-table-column prop="rank" label="#" width="48" align="center" />
            <el-table-column prop="defect_type" label="缺陷类型" min-width="90" />
            <el-table-column prop="production_line" label="产线" min-width="90" />
            <el-table-column prop="process" label="工序" min-width="80" />
            <el-table-column prop="product_code" label="产品编码" min-width="100" />
            <el-table-column prop="quantity" label="不良数量" min-width="90" align="right">
              <template #default="{ row }">
                <span class="qty-highlight">{{ row.quantity }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import QualityKpiCards from '../../components/quality/QualityKpiCards.vue'
import {
  fetchQualityKpi,
  fetchQualityTrend,
  fetchProcessYield,
  fetchDefectDistribution,
  fetchQualityAnomalies,
  fetchTopDefects,
} from '../../api/quality'

use([CanvasRenderer, LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const loading = ref(true)
const kpiPeriod = ref('day')
const kpiItems = ref([])
const trendGranularity = ref('day')
const trendPoints = ref([])
const processItems = ref([])
const defectTypeItems = ref([])
const defectLineItems = ref([])
const anomalies = ref([])
const topDefects = ref([])

const nowLabel = computed(() => {
  const d = new Date()
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
})

const chartTheme = {
  text: 'rgba(255,255,255,0.55)',
  grid: 'rgba(255,255,255,0.06)',
  axis: 'rgba(255,255,255,0.35)',
}

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: {
    data: ['良率', '不良率'],
    textStyle: { color: chartTheme.text, fontSize: 11 },
    top: 0,
    right: 0,
  },
  grid: { left: 48, right: 16, top: 32, bottom: 28 },
  xAxis: {
    type: 'category',
    data: trendPoints.value.map((p) => p.label),
    axisLine: { lineStyle: { color: chartTheme.grid } },
    axisLabel: { color: chartTheme.axis, fontSize: 10 },
  },
  yAxis: {
    type: 'value',
    min: 0,
    max: 100,
    axisLabel: { color: chartTheme.axis, formatter: '{value}%' },
    splitLine: { lineStyle: { color: chartTheme.grid } },
  },
  series: [
    {
      name: '良率',
      type: 'line',
      smooth: true,
      data: trendPoints.value.map((p) => p.yield_rate),
      lineStyle: { color: '#4ade80', width: 2 },
      itemStyle: { color: '#4ade80' },
      areaStyle: { color: 'rgba(74, 222, 128, 0.08)' },
    },
    {
      name: '不良率',
      type: 'line',
      smooth: true,
      data: trendPoints.value.map((p) => p.defect_rate),
      lineStyle: { color: '#f87171', width: 2 },
      itemStyle: { color: '#f87171' },
    },
  ],
}))

const processBarOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 80, right: 40, top: 8, bottom: 8 },
  xAxis: {
    type: 'value',
    max: 100,
    axisLabel: { color: chartTheme.axis, formatter: '{value}%' },
    splitLine: { lineStyle: { color: chartTheme.grid } },
  },
  yAxis: {
    type: 'category',
    data: processItems.value.map((i) => i.process),
    axisLabel: { color: chartTheme.axis, fontSize: 11 },
    axisLine: { show: false },
    axisTick: { show: false },
  },
  series: [
    {
      type: 'bar',
      data: processItems.value.map((i) => i.yield_rate),
      barWidth: 14,
      itemStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 1,
          y2: 0,
          colorStops: [
            { offset: 0, color: '#1e6b8a' },
            { offset: 1, color: '#38bdf8' },
          ],
        },
        borderRadius: [0, 3, 3, 0],
      },
      label: {
        show: true,
        position: 'right',
        formatter: '{c}%',
        color: chartTheme.text,
        fontSize: 10,
      },
    },
  ],
}))

const defectTypeOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: {
    orient: 'vertical',
    right: 8,
    top: 'center',
    textStyle: { color: chartTheme.text, fontSize: 10 },
  },
  series: [
    {
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['38%', '50%'],
      data: defectTypeItems.value.map((i) => ({ name: i.name, value: i.value })),
      label: { show: false },
      itemStyle: {
        borderColor: '#141b24',
        borderWidth: 2,
      },
      color: ['#4ade80', '#38bdf8', '#fbbf24', '#f87171', '#a78bfa', '#fb923c', '#94a3b8'],
    },
  ],
}))

const defectLineOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 48, right: 16, top: 16, bottom: 28 },
  xAxis: {
    type: 'category',
    data: defectLineItems.value.map((i) => i.name),
    axisLabel: { color: chartTheme.axis, fontSize: 10, rotate: 20 },
    axisLine: { lineStyle: { color: chartTheme.grid } },
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: chartTheme.axis },
    splitLine: { lineStyle: { color: chartTheme.grid } },
  },
  series: [
    {
      type: 'bar',
      data: defectLineItems.value.map((i) => i.value),
      barWidth: 20,
      itemStyle: {
        color: '#f87171',
        borderRadius: [3, 3, 0, 0],
      },
    },
  ],
}))

function formatTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function severityTagType(severity) {
  if (severity === 'critical') return 'danger'
  if (severity === 'major') return 'warning'
  return 'info'
}

function severityLabel(severity) {
  const map = { critical: '严重', major: '重要', minor: '一般' }
  return map[severity] || severity
}

async function loadKpi() {
  const data = await fetchQualityKpi(kpiPeriod.value)
  kpiItems.value = data.items
}

async function loadTrend() {
  const data = await fetchQualityTrend(trendGranularity.value, 30)
  trendPoints.value = data.points
}

async function loadAll() {
  loading.value = true
  try {
    const [kpi, trend, process, typeDist, lineDist, anomalyData, topData] = await Promise.all([
      fetchQualityKpi(kpiPeriod.value),
      fetchQualityTrend(trendGranularity.value, 30),
      fetchProcessYield(),
      fetchDefectDistribution('type'),
      fetchDefectDistribution('line'),
      fetchQualityAnomalies('open', 20),
      fetchTopDefects(10),
    ])
    kpiItems.value = kpi.items
    trendPoints.value = trend.points
    processItems.value = process.items
    defectTypeItems.value = typeDist.items
    defectLineItems.value = lineDist.items
    anomalies.value = anomalyData.items
    topDefects.value = topData.items
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.quality-dashboard {
  min-height: 100%;
  background: #0f1419;
  color: #e2e8f0;
  padding: 16px 20px 24px;
  box-sizing: border-box;
}

.qd-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.header-main {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}

.header-badge {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #4ade80;
  background: rgba(74, 222, 128, 0.12);
  padding: 3px 8px;
  border-radius: 3px;
  border: 1px solid rgba(74, 222, 128, 0.25);
}

.header-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #f1f5f9;
}

.header-sub {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-time {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  font-variant-numeric: tabular-nums;
}

.screen-primary {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 14px;
  margin-bottom: 14px;
  align-items: start;
}

.alert-panel {
  background: rgba(248, 113, 113, 0.06);
  border: 1px solid rgba(248, 113, 113, 0.18);
  border-radius: 6px;
  padding: 12px 14px;
  min-height: 96px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.panel-title {
  font-size: 14px;
  font-weight: 500;
  color: #f1f5f9;
  display: flex;
  align-items: center;
  gap: 6px;
}

.alert-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f87171;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.alert-count {
  font-size: 12px;
  color: #f87171;
}

.panel-hint {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
}

.screen-analysis {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 14px;
  margin-bottom: 14px;
}

.screen-detail {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 14px;
}

.detail-left {
  display: grid;
  grid-template-rows: 1fr 1fr;
  gap: 14px;
}

.chart-panel {
  background: #141b24;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 12px 14px;
}

.trend-panel {
  min-height: 280px;
}

.process-panel {
  min-height: 280px;
}

.chart-box {
  width: 100%;
  height: 230px;
}

.donut-chart,
.bar-chart {
  height: 200px;
}

.table-panel {
  min-height: 100%;
}

.rank-table {
  width: 100%;
}

.qty-highlight {
  color: #f87171;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

:deep(.alert-table),
:deep(.rank-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.04);
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.04);
  --el-table-text-color: rgba(255, 255, 255, 0.75);
  --el-table-header-text-color: rgba(255, 255, 255, 0.5);
  --el-table-border-color: rgba(255, 255, 255, 0.06);
  background: transparent;
}

:deep(.el-radio-button__inner) {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.55);
}

:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: rgba(74, 222, 128, 0.15);
  border-color: rgba(74, 222, 128, 0.35);
  color: #4ade80;
  box-shadow: none;
}

@media (max-width: 1100px) {
  .screen-primary {
    grid-template-columns: 1fr;
  }

  .screen-analysis,
  .screen-detail {
    grid-template-columns: 1fr;
  }

  .detail-left {
    grid-template-rows: auto auto;
  }
}
</style>
