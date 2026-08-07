<template>
  <div v-loading="loading" class="production-kanban">
    <header class="kanban-header">
      <h1 class="kanban-title">生产看板</h1>
      <div class="kanban-datetime">
        <span class="datetime-text">{{ data.display_time }}</span>
        <span class="weekday-text">{{ data.weekday }}</span>
      </div>
    </header>

    <div class="kanban-grid">
      <!-- 左列 -->
      <div class="kanban-col-left">
        <!-- 顶行双仪表盘 -->
        <div class="gauge-row">
          <div class="kanban-card gauge-card">
            <div class="card-title">产量达成率</div>
            <div class="gauge-body">
              <v-chart class="gauge-chart" :option="achievementGaugeOption" autoresize />
              <div class="gauge-value">{{ formatGaugeValue(data.achievement_rate) }}</div>
            </div>
          </div>
          <div class="kanban-card gauge-card">
            <div class="card-title">产量面积</div>
            <div class="gauge-body">
              <v-chart class="gauge-chart" :option="areaGaugeOption" autoresize />
              <div class="gauge-value">{{ formatGaugeValue(data.production_area) }}</div>
            </div>
          </div>
        </div>

        <!-- 底行：生产信息详细 -->
        <div class="kanban-card table-card detail-card">
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

      <!-- 右列 -->
      <div class="kanban-col-right">
        <!-- 生产信息统计 -->
        <div class="kanban-card table-card stats-card">
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

        <!-- 完成数统计图表 -->
        <div class="kanban-card chart-card">
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

function buildGaugeOption(value) {
  return {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        center: ['50%', '75%'],
        radius: '110%',
        min: 0,
        max: 100,
        splitNumber: 5,
        axisLine: {
          lineStyle: {
            width: 16,
            color: [
              [Math.min(value / 100, 1), '#f5a623'],
              [1, 'rgba(4, 10, 26, 0.5)'],
            ],
          },
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
          length: '52%',
          width: 7,
          offsetCenter: [0, '-6%'],
          itemStyle: { color: '#0a1a3a' },
        },
        axisTick: {
          show: true,
          length: 4,
          distance: -18,
          lineStyle: { color: 'rgba(255,255,255,0.15)', width: 1 },
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
  buildGaugeOption(data.achievement_rate),
)

const areaGaugeOption = computed(() =>
  buildGaugeOption(data.production_area),
)

const completionBarOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(10, 26, 58, 0.95)',
    borderColor: 'rgba(64, 224, 208, 0.3)',
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
.production-kanban {
  margin: -16px -20px;
  min-height: calc(100vh - 120px);
  padding: 12px 16px 16px;
  background: #040a1a;
  color: #fff;
  box-sizing: border-box;
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

.kanban-datetime {
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
  color: #40e0d0;
  font-family: 'Courier New', monospace;
}

.weekday-text {
  font-size: 13px;
  color: rgba(64, 224, 208, 0.75);
}

.kanban-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  height: calc(100vh - 180px);
  min-height: 560px;
}

.kanban-col-left,
.kanban-col-right {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.gauge-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  flex-shrink: 0;
}

.kanban-card {
  border-radius: 8px;
  border: 1px solid rgba(64, 224, 208, 0.12);
  overflow: hidden;
}

.card-title {
  text-align: center;
  font-size: 15px;
  font-weight: 500;
  color: #40e0d0;
  padding: 10px 12px 6px;
  letter-spacing: 1px;
}

/* 仪表盘卡：橙色渐变底 */
.gauge-card {
  background: linear-gradient(
    180deg,
    rgba(245, 166, 35, 0.55) 0%,
    rgba(245, 166, 35, 0.25) 35%,
    rgba(10, 26, 58, 0.85) 100%
  );
  min-height: 180px;
  border-color: rgba(245, 166, 35, 0.25);
}

.gauge-body {
  position: relative;
  height: 130px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.gauge-chart {
  width: 100%;
  height: 110px;
}

.gauge-value {
  position: absolute;
  bottom: 8px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 36px;
  font-weight: 700;
  color: #f5a623;
  line-height: 1;
  text-shadow: 0 0 12px rgba(245, 166, 35, 0.4);
}

/* 深蓝底表格卡 / 图表卡 */
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
  overflow: auto;
  padding: 0 8px 8px;
}

.chart-wrap {
  flex: 1;
  min-height: 0;
  padding: 0 8px 12px;
}

.bar-chart {
  width: 100%;
  height: 100%;
  min-height: 240px;
}

/* 深色表格样式 */
.dark-table {
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
  background: rgba(64, 224, 208, 0.06) !important;
}

.load-error {
  text-align: center;
  color: #f56c6c;
  padding: 12px;
  font-size: 14px;
}
</style>
