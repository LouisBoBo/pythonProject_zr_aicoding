<template>
  <div v-loading="loading" class="production-overview">
    <header class="overview-header">
      <h1 class="overview-title">生产概览</h1>
      <div class="overview-datetime">
        <span class="datetime-text">{{ displayTime }}</span>
        <span class="weekday-text">{{ weekday }}</span>
      </div>
    </header>

    <div class="overview-grid">
      <div class="grid-row gauge-row">
        <div class="overview-card gauge-card gauge-rate">
          <div class="card-title card-title--orange">产量达成率</div>
          <div class="gauge-body">
            <v-chart class="gauge-chart" :option="achievementGaugeOption" autoresize />
            <div class="gauge-value">{{ formatGaugeValue(data.achievement_rate) }}</div>
          </div>
        </div>
        <div class="overview-card gauge-card gauge-area">
          <div class="card-title card-title--orange">产量面积</div>
          <div class="gauge-body">
            <v-chart class="gauge-chart" :option="areaGaugeOption" autoresize />
            <div class="gauge-value gauge-value-area">{{ formatGaugeValue(data.production_area) }}</div>
          </div>
        </div>
      </div>

      <div class="grid-row middle-row">
        <div class="overview-card kpi-card">
          <div class="card-title">生产信息统计</div>
          <div class="kpi-list">
            <div v-for="item in kpiItems" :key="item.key" class="kpi-row">
              <span class="kpi-label">{{ item.label }}</span>
              <div class="kpi-right">
                <span class="kpi-value">{{ item.displayValue }}</span>
                <span
                  v-if="item.trend"
                  class="kpi-trend"
                  :class="{
                    'kpi-trend--up': item.trend.direction === 'up',
                    'kpi-trend--down': item.trend.direction === 'down',
                  }"
                >
                  <span class="kpi-arrow">{{ item.trend.direction === 'up' ? '↑' : '↓' }}</span>
                  {{ item.trend.text }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div class="overview-card chart-card">
          <div class="card-title">完成数统计图表</div>
          <div class="chart-wrap">
            <v-chart class="bar-chart" :option="completionBarOption" autoresize />
          </div>
        </div>
      </div>

      <div class="grid-row detail-row">
        <div class="overview-card table-card">
          <div class="card-title">生产信息详细</div>
          <div class="table-wrap">
            <el-table
              :data="data.detail_rows"
              class="dark-table"
              :show-header="true"
              stripe
            >
              <el-table-column prop="time" label="时间" min-width="90" />
              <el-table-column prop="process_card_no" label="流程卡号" min-width="130" />
              <el-table-column prop="product_model" label="产品型号" min-width="90" />
              <el-table-column prop="quantity" label="数量" min-width="70" align="right" />
              <el-table-column prop="today_completed" label="今日完成数" min-width="95" align="right" />
              <el-table-column prop="total_completed" label="已完成总数" min-width="95" align="right" />
            </el-table>
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
import { BarChart, GaugeChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { fetchProductionOverview } from '../../api/productionOverview'

use([
  CanvasRenderer,
  BarChart,
  GaugeChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
])

const loading = ref(true)
const loadError = ref('')
const displayTime = ref('')
const weekday = ref('')

const defaultStats = {
  today_completed: 0,
  today_area_output: 0,
  today_defect_total: 0,
  daily_defect_rate: '0%',
  today_incoming_boards: 0,
  trends: {},
}

const defaultData = {
  achievement_rate: 0,
  production_area: 0,
  stats: { ...defaultStats },
  completion_chart: [],
  detail_rows: [],
}

const data = reactive({ ...defaultData })

function buildRateGaugeOption(value) {
  const ratio = Math.min(Math.max(value / 100, 0), 1)
  return {
    animation: true,
    animationDuration: 1200,
    animationEasing: 'cubicOut',
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        center: ['50%', '78%'],
        radius: '105%',
        min: 0,
        max: 100,
        splitNumber: 10,
        axisLine: {
          lineStyle: {
            width: 14,
            color: [
              [ratio, '#ff9900'],
              [1, 'rgba(4, 10, 26, 0.55)'],
            ],
          },
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
          length: '50%',
          width: 6,
          offsetCenter: [0, '-4%'],
          itemStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 1, y2: 1,
              colorStops: [
                { offset: 0, color: '#ffb347' },
                { offset: 1, color: '#ff6600' },
              ],
            },
          },
        },
        axisTick: {
          show: true,
          length: 3,
          distance: -16,
          lineStyle: { color: 'rgba(255, 255, 255, 0.2)', width: 1 },
        },
        splitLine: { show: false },
        axisLabel: { show: false },
        detail: { show: false },
        data: [{ value }],
      },
    ],
  }
}

function buildAreaGaugeOption(value) {
  const max = Math.max(10, Math.ceil(value / 5) * 5)
  const ratio = Math.min(value / max, 1)
  return {
    animation: true,
    animationDuration: 1200,
    animationEasing: 'cubicOut',
    series: [
      {
        type: 'gauge',
        startAngle: 200,
        endAngle: -20,
        center: ['50%', '72%'],
        radius: '95%',
        min: 0,
        max,
        splitNumber: 5,
        axisLine: {
          lineStyle: {
            width: 12,
            color: [
              [ratio, '#e8940f'],
              [1, 'rgba(4, 10, 26, 0.45)'],
            ],
          },
        },
        pointer: {
          length: '45%',
          width: 4,
          offsetCenter: [0, '0%'],
          itemStyle: { color: '#f5a623' },
        },
        axisTick: {
          show: true,
          length: 5,
          distance: -14,
          lineStyle: { color: 'rgba(245, 166, 35, 0.35)', width: 1 },
        },
        splitLine: {
          show: true,
          length: 8,
          distance: -14,
          lineStyle: { color: 'rgba(245, 166, 35, 0.2)', width: 1 },
        },
        axisLabel: { show: false },
        detail: { show: false },
        data: [{ value }],
      },
    ],
  }
}

const achievementGaugeOption = computed(() => buildRateGaugeOption(data.achievement_rate))
const areaGaugeOption = computed(() => buildAreaGaugeOption(data.production_area))

const kpiItems = computed(() => {
  const s = data.stats
  const t = s.trends || {}
  return [
    {
      key: 'today_completed',
      label: '今日完成数',
      displayValue: formatNumber(s.today_completed),
      trend: t.today_completed,
    },
    {
      key: 'today_area_output',
      label: '面积产量',
      displayValue: formatArea(s.today_area_output),
      trend: t.today_area_output,
    },
    {
      key: 'today_defect_total',
      label: '缺陷总数',
      displayValue: formatNumber(s.today_defect_total),
      trend: t.today_defect_total,
    },
    {
      key: 'daily_defect_rate',
      label: '不良率',
      displayValue: s.daily_defect_rate,
      trend: t.daily_defect_rate,
    },
    {
      key: 'today_incoming_boards',
      label: '来板数',
      displayValue: formatNumber(s.today_incoming_boards),
      trend: t.today_incoming_boards,
    },
  ]
})

const completionBarOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(10, 26, 58, 0.95)',
    borderColor: 'rgba(255, 153, 0, 0.25)',
    textStyle: { color: '#fff' },
  },
  legend: {
    data: ['LOT产出', '型号产出'],
    top: 4,
    right: 16,
    textStyle: { color: 'rgba(255, 255, 255, 0.7)', fontSize: 12 },
    itemWidth: 14,
    itemHeight: 8,
  },
  grid: { left: 56, right: 24, top: 36, bottom: 28 },
  xAxis: {
    type: 'category',
    data: data.completion_chart.map((p) => p.label),
    axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.15)' } },
    axisLabel: { color: 'rgba(255, 255, 255, 0.6)', fontSize: 11 },
    axisTick: { show: false },
  },
  yAxis: {
    type: 'value',
    max: 6000000,
    splitNumber: 6,
    axisLine: { show: false },
    axisLabel: {
      color: 'rgba(255, 255, 255, 0.5)',
      fontSize: 11,
      formatter: (v) => (v >= 1000000 ? `${v / 1000000}M` : v),
    },
    splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },
  },
  series: [
    {
      name: 'LOT产出',
      type: 'bar',
      barWidth: 20,
      barGap: '30%',
      data: data.completion_chart.map((p) => p.lot_output),
      itemStyle: {
        borderRadius: [3, 3, 0, 0],
        color: {
          type: 'linear',
          x: 0, y: 1, x2: 0, y2: 0,
          colorStops: [
            { offset: 0, color: '#1e3a8a' },
            { offset: 1, color: '#3b82f6' },
          ],
        },
      },
    },
    {
      name: '型号产出',
      type: 'bar',
      barWidth: 20,
      data: data.completion_chart.map((p) => p.model_output),
      itemStyle: {
        borderRadius: [3, 3, 0, 0],
        color: {
          type: 'linear',
          x: 0, y: 1, x2: 0, y2: 0,
          colorStops: [
            { offset: 0, color: '#0e7490' },
            { offset: 1, color: '#22d3ee' },
          ],
        },
      },
    },
  ],
}))

function formatGaugeValue(val) {
  if (Number.isInteger(val)) return String(val)
  return val.toFixed(1)
}

function formatNumber(val) {
  return Number(val).toLocaleString('zh-CN')
}

function formatArea(val) {
  return Number(val).toLocaleString('zh-CN', { maximumFractionDigits: 1 })
}

function applyData(resp) {
  Object.assign(data, {
    achievement_rate: resp.achievement_rate,
    production_area: resp.production_area,
    stats: resp.stats || { ...defaultStats },
    completion_chart: resp.completion_chart || [],
    detail_rows: resp.detail_rows || [],
  })
}

let clockTimer = null

function updateClock() {
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
  displayTime.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
  weekday.value = weekdays[now.getDay()]
}

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
    const resp = await fetchProductionOverview()
    applyData(resp)
  } catch (err) {
    loadError.value = err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
  loadData()
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
})
</script>

<style scoped>
.production-overview {
  margin: -16px -20px;
  width: calc(100% + 40px);
  max-width: calc(100% + 40px);
  min-width: 0;
  min-height: 100%;
  padding: 10px 14px 14px;
  background: #040a1a;
  color: #fff;
  box-sizing: border-box;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
}

.overview-header {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-bottom: 10px;
  padding: 2px 0 6px;
  flex-shrink: 0;
}

.overview-title {
  margin: 0;
  font-size: 26px;
  font-weight: 600;
  color: #fff;
  letter-spacing: 4px;
}

.overview-datetime {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.datetime-text {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
  font-family: 'Courier New', monospace;
}

.weekday-text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
}

.overview-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-height: 0;
  width: 100%;
  max-width: 100%;
}

.grid-row {
  min-width: 0;
  max-width: 100%;
}

.gauge-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
  flex-shrink: 0;
}

.middle-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
  flex: 1;
  min-height: 200px;
}

.detail-row {
  flex-shrink: 0;
  min-height: 160px;
  max-height: 220px;
}

.overview-card {
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
  min-width: 0;
  max-width: 100%;
}

.card-title {
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
  padding: 8px 12px 4px;
  letter-spacing: 1px;
}

.card-title--orange {
  color: #ff9900;
}

.gauge-card {
  min-height: 180px;
}

.gauge-rate {
  background: linear-gradient(
    180deg,
    rgba(255, 153, 0, 0.62) 0%,
    rgba(255, 153, 0, 0.28) 38%,
    rgba(10, 26, 58, 0.88) 100%
  );
  border-color: rgba(255, 153, 0, 0.35);
}

.gauge-area {
  background: linear-gradient(
    160deg,
    rgba(232, 148, 15, 0.45) 0%,
    rgba(245, 166, 35, 0.12) 45%,
    rgba(10, 26, 58, 0.92) 100%
  );
  border-color: rgba(245, 166, 35, 0.28);
}

.gauge-body {
  position: relative;
  height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
  overflow: hidden;
}

.gauge-chart {
  width: 100%;
  height: 100px;
  min-width: 0;
}

.gauge-value {
  position: absolute;
  bottom: 6px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 32px;
  font-weight: 700;
  color: #ff9900;
  line-height: 1;
}

.gauge-value-area {
  font-size: 34px;
  color: #ffb84d;
}

.kpi-card,
.chart-card,
.table-card {
  background: #0a1a3a;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.kpi-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
  padding: 4px 16px 12px;
  gap: 2px;
}

.kpi-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 4px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.kpi-row:last-child {
  border-bottom: none;
}

.kpi-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.55);
  flex-shrink: 0;
}

.kpi-right {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.kpi-value {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}

.kpi-trend {
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.kpi-trend--up {
  color: #ff9900;
}

.kpi-trend--down {
  color: rgba(255, 255, 255, 0.45);
}

.kpi-arrow {
  font-size: 13px;
  line-height: 1;
}

.chart-wrap {
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  padding: 0 8px 10px;
}

.bar-chart {
  width: 100%;
  height: 100%;
  min-height: 180px;
  min-width: 0;
}

.table-wrap {
  flex: 1;
  min-width: 0;
  max-width: 100%;
  overflow-x: auto;
  overflow-y: auto;
  padding: 0 8px 8px;
}

.dark-table {
  width: 100%;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(6, 20, 48, 0.95);
  --el-table-row-hover-bg-color: rgba(255, 153, 0, 0.06);
  --el-table-border-color: transparent;
  --el-table-text-color: rgba(255, 255, 255, 0.85);
  --el-table-header-text-color: rgba(255, 255, 255, 0.75);
  background: transparent !important;
}

.dark-table :deep(.el-table__inner-wrapper)::before {
  display: none;
}

.dark-table :deep(th.el-table__cell) {
  background: rgba(6, 20, 48, 0.95) !important;
  color: rgba(255, 255, 255, 0.75) !important;
  font-weight: 500;
  font-size: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
  padding: 7px 0;
}

.dark-table :deep(td.el-table__cell) {
  background: transparent !important;
  color: rgba(255, 255, 255, 0.82) !important;
  font-size: 12px;
  border-bottom: none !important;
  padding: 6px 0;
}

.dark-table :deep(.el-table__row--striped td.el-table__cell) {
  background: rgba(255, 255, 255, 0.02) !important;
}

.dark-table :deep(.el-table__body tr:hover > td.el-table__cell) {
  background: rgba(255, 153, 0, 0.06) !important;
}

.load-error {
  text-align: center;
  color: #f56c6c;
  padding: 12px;
  font-size: 14px;
}
</style>
