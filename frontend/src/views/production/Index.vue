<template>
  <div v-loading="loading" class="production-overview">
    <header class="overview-header">
      <h1 class="overview-title">生产概览</h1>
      <div class="overview-datetime">
        <span class="datetime-text">{{ data.display_time }}</span>
        <span class="weekday-text">{{ data.weekday }}</span>
      </div>
    </header>

    <div class="overview-grid">
      <div class="overview-col-left">
        <div class="gauge-row">
          <div class="overview-card gauge-card gauge-card--orange">
            <div class="card-title">产量达成率</div>
            <div class="gauge-body">
              <v-chart class="gauge-chart" :option="achievementGaugeOption" autoresize />
              <div class="gauge-value gauge-value--orange">
                {{ formatGaugeValue(data.achievement_rate) }}
              </div>
            </div>
          </div>
          <div class="overview-card gauge-card gauge-card--yellow">
            <div class="card-title">产量面积</div>
            <div class="gauge-body">
              <v-chart class="gauge-chart" :option="areaGaugeOption" autoresize />
              <div class="gauge-value gauge-value--yellow">
                {{ formatGaugeValue(data.production_area) }}
              </div>
            </div>
          </div>
        </div>

        <div class="overview-card table-card">
          <div class="card-title">生产信息详细</div>
          <div class="table-wrap">
            <el-table
              :data="data.detail_rows"
              class="dark-table"
              :show-header="true"
              stripe
            >
              <el-table-column prop="time" label="时间" min-width="100" />
              <el-table-column prop="process_card_no" label="流程卡号" min-width="140" />
              <el-table-column prop="product_model" label="产品型号" min-width="100" />
              <el-table-column prop="quantity" label="数量" min-width="80" align="right" />
              <el-table-column prop="today_completed" label="今日完成数" min-width="100" align="right" />
              <el-table-column prop="total_completed" label="已完成总数" min-width="100" align="right" />
            </el-table>
          </div>
        </div>
      </div>

      <div class="overview-col-right">
        <div class="overview-card table-card">
          <div class="card-title">生产信息统计</div>
          <div class="table-wrap">
            <el-table
              :data="data.stats_rows"
              class="dark-table"
              :show-header="true"
              stripe
            >
              <el-table-column prop="time" label="时间" min-width="80" />
              <el-table-column prop="today_completed" label="今日完成数" min-width="100" align="right" />
              <el-table-column prop="today_area_output" label="今日面积产量" min-width="110" align="right">
                <template #default="{ row }">
                  {{ formatArea(row.today_area_output) }}
                </template>
              </el-table-column>
              <el-table-column prop="today_defect_total" label="今日缺陷总数" min-width="110" align="right" />
              <el-table-column prop="daily_defect_rate" label="日不良率" min-width="90" align="right" />
              <el-table-column prop="today_incoming_boards" label="今日来板数" min-width="100" align="right" />
            </el-table>
          </div>
        </div>

        <div class="overview-card chart-card">
          <div class="card-title">完成数统计图表</div>
          <div class="chart-wrap">
            <v-chart class="bar-chart" :option="completionBarOption" autoresize />
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
import { fetchProductionKanban } from '../../api/kanbanProduction'

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

const defaultData = {
  display_time: '',
  weekday: '',
  achievement_rate: 0,
  production_area: 0,
  stats_rows: [],
  detail_rows: [],
  completion_chart: [],
}

const data = reactive({ ...defaultData })

function buildGaugeOption(value, accentColor) {
  return {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        center: ['50%', '75%'],
        radius: '100%',
        min: 0,
        max: 100,
        splitNumber: 5,
        axisLine: {
          lineStyle: {
            width: 14,
            color: [
              [Math.min(value / 100, 1), accentColor],
              [1, 'rgba(4, 10, 26, 0.55)'],
            ],
          },
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
          length: '50%',
          width: 6,
          offsetCenter: [0, '-6%'],
          itemStyle: { color: accentColor },
        },
        axisTick: {
          show: true,
          length: 4,
          distance: -16,
          lineStyle: { color: 'rgba(255,255,255,0.18)', width: 1 },
        },
        splitLine: { show: false },
        axisLabel: { show: false },
        detail: { show: false },
        data: [{ value }],
      },
    ],
  }
}

const achievementGaugeOption = computed(() =>
  buildGaugeOption(data.achievement_rate, '#ff9900'),
)

const areaGaugeOption = computed(() =>
  buildGaugeOption(data.production_area, '#ffc107'),
)

const completionBarOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(10, 26, 58, 0.95)',
    borderColor: 'rgba(0, 242, 255, 0.3)',
    textStyle: { color: '#fff' },
  },
  legend: {
    data: ['LOT产出', '型号产出'],
    top: 4,
    right: 16,
    textStyle: { color: 'rgba(255,255,255,0.75)', fontSize: 12 },
    itemWidth: 14,
    itemHeight: 8,
  },
  grid: { left: 60, right: 24, top: 40, bottom: 32 },
  xAxis: {
    type: 'category',
    data: data.completion_chart.map((p) => p.label),
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
    axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 11 },
    axisTick: { show: false },
  },
  yAxis: {
    type: 'value',
    max: 6000000,
    splitNumber: 6,
    axisLine: { show: false },
    axisLabel: {
      color: 'rgba(255,255,255,0.5)',
      fontSize: 11,
      formatter: (v) => (v >= 1000000 ? `${v / 1000000}M` : v),
    },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
  },
  series: [
    {
      name: 'LOT产出',
      type: 'bar',
      barWidth: 18,
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
      barWidth: 18,
      data: data.completion_chart.map((p) => p.model_output),
      itemStyle: {
        borderRadius: [3, 3, 0, 0],
        color: {
          type: 'linear',
          x: 0, y: 1, x2: 0, y2: 0,
          colorStops: [
            { offset: 0, color: '#0e7490' },
            { offset: 1, color: '#00f2fe' },
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

function formatArea(val) {
  return Number(val).toLocaleString('zh-CN', { maximumFractionDigits: 1 })
}

function applyData(resp) {
  Object.assign(data, {
    display_time: resp.display_time,
    weekday: resp.weekday,
    achievement_rate: resp.achievement_rate,
    production_area: resp.production_area,
    stats_rows: resp.stats_rows || [],
    detail_rows: resp.detail_rows || [],
    completion_chart: resp.completion_chart || [],
  })
}

let clockTimer = null

function updateClock() {
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
  data.display_time = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
  data.weekday = weekdays[now.getDay()]
}

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
    const resp = await fetchProductionKanban({ boardCategory: 'production' })
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
  min-height: calc(100vh - 120px);
  padding: 12px 16px 16px;
  background: #000a1a;
  color: #fff;
  box-sizing: border-box;
  overflow-x: hidden;
}

.overview-header {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-bottom: 12px;
  padding: 4px 0 8px;
}

.overview-title {
  margin: 0;
  font-size: 28px;
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
  font-size: 14px;
  color: #00f2ff;
  font-family: 'Courier New', monospace;
}

.weekday-text {
  font-size: 13px;
  color: rgba(0, 242, 255, 0.75);
}

.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  height: calc(100vh - 180px);
  min-height: 560px;
  width: 100%;
  max-width: 100%;
  min-width: 0;
}

.overview-col-left,
.overview-col-right {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

.gauge-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  flex-shrink: 0;
  min-width: 0;
  max-width: 100%;
}

.overview-card {
  border-radius: 10px;
  border: 1px solid rgba(0, 242, 255, 0.15);
  overflow: hidden;
  min-width: 0;
  max-width: 100%;
}

.card-title {
  text-align: center;
  font-size: 15px;
  font-weight: 500;
  color: #00f2ff;
  padding: 10px 12px 6px;
  letter-spacing: 1px;
}

.gauge-card {
  min-height: 180px;
}

.gauge-card--orange {
  background: linear-gradient(
    180deg,
    rgba(255, 153, 0, 0.62) 0%,
    rgba(255, 153, 0, 0.28) 38%,
    rgba(10, 26, 58, 0.88) 100%
  );
  border-color: rgba(255, 153, 0, 0.35);
}

.gauge-card--yellow {
  background: linear-gradient(
    180deg,
    rgba(255, 193, 7, 0.58) 0%,
    rgba(255, 193, 7, 0.26) 38%,
    rgba(10, 26, 58, 0.88) 100%
  );
  border-color: rgba(255, 193, 7, 0.32);
}

.gauge-body {
  position: relative;
  height: 130px;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

.gauge-chart {
  width: 100%;
  max-width: 100%;
  height: 110px;
  min-width: 0;
}

.gauge-value {
  position: absolute;
  bottom: 8px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
}

.gauge-value--orange {
  color: #ff9900;
  text-shadow: 0 0 14px rgba(255, 153, 0, 0.45);
}

.gauge-value--yellow {
  color: #ffc107;
  text-shadow: 0 0 14px rgba(255, 193, 7, 0.45);
}

.table-card,
.chart-card {
  background: #0a1a3a;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.table-wrap {
  flex: 1;
  min-width: 0;
  max-width: 100%;
  overflow-x: auto;
  overflow-y: auto;
  padding: 0 8px 8px;
}

.chart-wrap {
  flex: 1;
  min-height: 0;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  padding: 0 8px 12px;
}

.bar-chart {
  width: 100%;
  max-width: 100%;
  height: 100%;
  min-height: 240px;
  min-width: 0;
}

.dark-table {
  width: max-content;
  min-width: 100%;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(10, 40, 80, 0.85);
  --el-table-row-hover-bg-color: rgba(0, 242, 255, 0.06);
  --el-table-border-color: transparent;
  --el-table-text-color: rgba(255, 255, 255, 0.85);
  --el-table-header-text-color: #00f2ff;
  background: transparent !important;
}

.dark-table :deep(.el-table__inner-wrapper)::before {
  display: none;
}

.dark-table :deep(th.el-table__cell) {
  background: rgba(10, 40, 80, 0.85) !important;
  color: #00f2ff !important;
  font-weight: 500;
  font-size: 13px;
  border-bottom: 1px solid rgba(0, 242, 255, 0.15) !important;
  padding: 8px 0;
}

.dark-table :deep(td.el-table__cell) {
  background: transparent !important;
  color: rgba(255, 255, 255, 0.82) !important;
  font-size: 13px;
  border-bottom: none !important;
  padding: 7px 0;
}

.dark-table :deep(.el-table__row--striped td.el-table__cell) {
  background: rgba(255, 255, 255, 0.02) !important;
}

.dark-table :deep(.el-table__body tr:hover > td.el-table__cell) {
  background: rgba(0, 242, 255, 0.06) !important;
}

.load-error {
  text-align: center;
  color: #f56c6c;
  padding: 12px;
  font-size: 14px;
}
</style>
