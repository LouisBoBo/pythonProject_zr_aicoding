<template>
  <div v-loading="loading" class="production-overview">
    <div class="kpi-banner">
      <div
        v-for="tile in topKpiTiles"
        :key="tile.key"
        class="kpi-tile"
        :class="`kpi-tile--${tile.accent}`"
      >
        <div class="kpi-tile-label">{{ tile.label }}</div>
        <div class="kpi-tile-main">
          <span class="kpi-tile-value">{{ tile.displayValue }}</span>
          <span
            v-if="tile.trend"
            class="kpi-tile-trend"
            :class="tile.trend.direction === 'up' ? 'kpi-tile-trend--up' : 'kpi-tile-trend--down'"
          >
            {{ tile.trend.direction === 'up' ? '↑' : '↓' }} {{ tile.trend.text }}
          </span>
        </div>
        <div class="kpi-tile-bar">
          <div class="kpi-tile-bar-fill" :style="{ width: `${tile.barPercent}%` }" />
        </div>
      </div>
    </div>

    <div class="main-body">
      <div class="panel panel-table">
        <div class="panel-head">生产信息详细</div>
        <div class="table-wrap">
          <el-table
            :data="data.detail_rows"
            class="compact-table"
            :show-header="true"
            :row-class-name="tableRowClass"
          >
            <el-table-column prop="time" label="时间" min-width="88" />
            <el-table-column prop="process_card_no" label="流程卡号" min-width="128" />
            <el-table-column prop="product_model" label="产品型号" min-width="88" />
            <el-table-column prop="quantity" label="数量" min-width="64" align="right" />
            <el-table-column prop="today_completed" label="今日完成数" min-width="92" align="right" />
            <el-table-column prop="total_completed" label="已完成总数" min-width="92" align="right" />
          </el-table>
        </div>
      </div>

      <div class="right-stack">
        <div class="panel panel-chart">
          <div class="panel-head">完成数统计图表</div>
          <div class="chart-wrap">
            <v-chart class="bar-chart" :option="completionBarOption" autoresize />
          </div>
        </div>

        <div class="mini-metrics">
          <div class="mini-metric mini-metric--defect">
            <div class="mini-metric-label">缺陷总数</div>
            <div class="mini-metric-value">{{ formatNumber(data.stats.today_defect_total) }}</div>
            <div
              v-if="data.stats.trends?.today_defect_total"
              class="mini-metric-trend"
              :class="data.stats.trends.today_defect_total.direction === 'down' ? 'mini-metric-trend--good' : 'mini-metric-trend--warn'"
            >
              {{ data.stats.trends.today_defect_total.direction === 'up' ? '↑' : '↓' }}
              {{ data.stats.trends.today_defect_total.text }}
            </div>
          </div>
          <div class="mini-metric mini-metric--incoming">
            <div class="mini-metric-label">今日来板数</div>
            <div class="mini-metric-value">{{ formatNumber(data.stats.today_incoming_boards) }}</div>
            <div
              v-if="data.stats.trends?.today_incoming_boards"
              class="mini-metric-trend mini-metric-trend--up"
            >
              ↑ {{ data.stats.trends.today_incoming_boards.text }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loadError" class="load-error">{{ loadError }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
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
  GridComponent,
  TooltipComponent,
  LegendComponent,
])

const loading = ref(true)
const loadError = ref('')

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

const topKpiTiles = computed(() => {
  const s = data.stats
  const t = s.trends || {}
  return [
    {
      key: 'achievement_rate',
      label: '产量达成率',
      displayValue: `${formatGaugeValue(data.achievement_rate)}%`,
      trend: t.achievement_rate,
      barPercent: Math.min(data.achievement_rate, 100),
      accent: 'steel',
    },
    {
      key: 'production_area',
      label: '产量面积',
      displayValue: formatGaugeValue(data.production_area),
      trend: t.production_area,
      barPercent: Math.min((data.production_area / 10) * 100, 100),
      accent: 'slate',
    },
    {
      key: 'today_completed',
      label: '今日完成数',
      displayValue: formatNumber(s.today_completed),
      trend: t.today_completed,
      barPercent: Math.min((s.today_completed / 5000) * 100, 100),
      accent: 'blue',
    },
    {
      key: 'daily_defect_rate',
      label: '日不良率',
      displayValue: s.daily_defect_rate,
      trend: t.daily_defect_rate,
      barPercent: Math.min(parseFloat(s.daily_defect_rate) * 15 || 0, 100),
      accent: 'amber',
    },
  ]
})

const completionBarOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(44, 62, 80, 0.95)',
    borderColor: 'rgba(91, 141, 239, 0.4)',
    textStyle: { color: '#ecf0f1' },
  },
  legend: {
    data: ['LOT产出', '型号产出'],
    top: 2,
    right: 8,
    textStyle: { color: '#5a6d82', fontSize: 11 },
    itemWidth: 12,
    itemHeight: 8,
  },
  grid: { left: 48, right: 12, top: 32, bottom: 24 },
  xAxis: {
    type: 'category',
    data: data.completion_chart.map((p) => p.label),
    axisLine: { lineStyle: { color: '#b8c5d4' } },
    axisLabel: { color: '#5a6d82', fontSize: 11 },
    axisTick: { show: false },
  },
  yAxis: {
    type: 'value',
    max: 6000000,
    splitNumber: 4,
    axisLine: { show: false },
    axisLabel: {
      color: '#7a8fa6',
      fontSize: 10,
      formatter: (v) => (v >= 1000000 ? `${v / 1000000}M` : v),
    },
    splitLine: { lineStyle: { color: '#d0dae6' } },
  },
  series: [
    {
      name: 'LOT产出',
      type: 'bar',
      barWidth: 16,
      barGap: '25%',
      data: data.completion_chart.map((p) => p.lot_output),
      itemStyle: {
        borderRadius: [2, 2, 0, 0],
        color: '#4a6fa5',
      },
    },
    {
      name: '型号产出',
      type: 'bar',
      barWidth: 16,
      data: data.completion_chart.map((p) => p.model_output),
      itemStyle: {
        borderRadius: [2, 2, 0, 0],
        color: '#7a9cc6',
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

function tableRowClass() {
  return 'compact-row'
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
  loadData()
})
</script>

<style scoped>
.production-overview {
  margin: -16px -20px;
  width: calc(100% + 40px);
  max-width: calc(100% + 40px);
  min-width: 0;
  min-height: 100%;
  padding: 14px 16px 16px;
  background: #dfe6ed;
  color: #2c3e50;
  box-sizing: border-box;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.kpi-banner {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  flex-shrink: 0;
}

.kpi-tile {
  background: #f4f7fa;
  border: 1px solid #c5d0dc;
  border-radius: 8px;
  padding: 12px 14px 10px;
  min-width: 0;
}

.kpi-tile--steel { border-top: 3px solid #4a6fa5; }
.kpi-tile--slate { border-top: 3px solid #5a6d82; }
.kpi-tile--blue { border-top: 3px solid #5b8def; }
.kpi-tile--amber { border-top: 3px solid #c49a3a; }

.kpi-tile-label {
  font-size: 12px;
  color: #5a6d82;
  margin-bottom: 6px;
}

.kpi-tile-main {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}

.kpi-tile-value {
  font-size: 26px;
  font-weight: 700;
  color: #2c3e50;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.kpi-tile-trend {
  font-size: 12px;
  font-weight: 500;
}

.kpi-tile-trend--up { color: #3d8b5f; }
.kpi-tile-trend--down { color: #a06850; }

.kpi-tile-bar {
  margin-top: 10px;
  height: 4px;
  background: #d0dae6;
  border-radius: 2px;
  overflow: hidden;
}

.kpi-tile-bar-fill {
  height: 100%;
  background: #4a6fa5;
  border-radius: 2px;
  transition: width 0.6s ease;
}

.kpi-tile--amber .kpi-tile-bar-fill { background: #c49a3a; }

.main-body {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
  gap: 10px;
  flex: 1;
  min-height: 0;
}

.panel {
  background: #f4f7fa;
  border: 1px solid #c5d0dc;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

.panel-head {
  padding: 10px 14px 8px;
  font-size: 13px;
  font-weight: 600;
  color: #3d5166;
  border-bottom: 1px solid #d0dae6;
  flex-shrink: 0;
}

.panel-table {
  min-height: 280px;
}

.right-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  min-width: 0;
}

.panel-chart {
  flex: 1;
  min-height: 180px;
}

.chart-wrap {
  flex: 1;
  min-height: 0;
  padding: 4px 8px 8px;
}

.bar-chart {
  width: 100%;
  height: 100%;
  min-height: 160px;
}

.table-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0 6px 6px;
}

.compact-table {
  width: 100%;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: #e8edf2;
  --el-table-row-hover-bg-color: #eef3f8;
  --el-table-border-color: #d0dae6;
  --el-table-text-color: #3d5166;
  --el-table-header-text-color: #5a6d82;
}

.compact-table :deep(.el-table__inner-wrapper)::before {
  display: none;
}

.compact-table :deep(th.el-table__cell) {
  background: #e8edf2 !important;
  color: #5a6d82 !important;
  font-weight: 600;
  font-size: 12px;
  padding: 6px 0;
  border-bottom: 1px solid #d0dae6 !important;
}

.compact-table :deep(td.el-table__cell) {
  background: transparent !important;
  color: #3d5166 !important;
  font-size: 12px;
  padding: 5px 0;
  border-bottom: 1px solid #e4eaf0 !important;
}

.compact-table :deep(.compact-row) {
  transition: background 0.15s;
}

.compact-table :deep(.compact-row:hover > td.el-table__cell) {
  background: #eef3f8 !important;
}

.compact-table :deep(.compact-row:hover > td.el-table__cell:first-child) {
  box-shadow: inset 3px 0 0 #4a6fa5;
}

.mini-metrics {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
  flex-shrink: 0;
}

.mini-metric {
  background: #f4f7fa;
  border: 1px solid #c5d0dc;
  border-radius: 8px;
  padding: 12px 14px;
  min-width: 0;
}

.mini-metric--defect {
  border-left: 3px solid #a06850;
}

.mini-metric--incoming {
  border-left: 3px solid #3d8b5f;
}

.mini-metric-label {
  font-size: 11px;
  color: #7a8fa6;
  margin-bottom: 4px;
}

.mini-metric-value {
  font-size: 22px;
  font-weight: 700;
  color: #2c3e50;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}

.mini-metric-trend {
  margin-top: 4px;
  font-size: 11px;
  font-weight: 500;
}

.mini-metric-trend--good { color: #3d8b5f; }
.mini-metric-trend--warn { color: #a06850; }
.mini-metric-trend--up { color: #3d8b5f; }

.load-error {
  text-align: center;
  color: #c0392b;
  padding: 10px;
  font-size: 13px;
}
</style>
