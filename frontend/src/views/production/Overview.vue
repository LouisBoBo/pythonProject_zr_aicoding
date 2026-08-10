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
            :class="tile.trendClass"
          >
            {{ tile.trend.direction === 'up' ? '↑' : '↓' }} {{ tile.trend.text }}
          </span>
          <span
            v-if="tile.statusTag"
            class="kpi-status-tag"
            :class="tile.statusTag.class"
          >
            {{ tile.statusTag.label }}
          </span>
        </div>
        <div v-if="tile.subLine" class="kpi-tile-sub">{{ tile.subLine }}</div>
        <div v-if="tile.barPercent != null" class="kpi-tile-bar">
          <div class="kpi-tile-bar-fill" :style="{ width: `${tile.barPercent}%` }" />
        </div>
      </div>
    </div>

    <div class="main-body">
      <div class="panel panel-timeline">
        <div class="panel-head">
          <span class="panel-title">生产进度时间线</span>
          <span class="panel-meta">最近 {{ timelineItems.length }} 条</span>
        </div>
        <div class="timeline-wrap">
          <div
            v-for="(item, idx) in timelineItems"
            :key="item.process_card_no + idx"
            class="timeline-item"
          >
            <div class="timeline-axis">
              <span class="timeline-dot" :class="`timeline-dot--${item.status.type}`" />
              <span v-if="idx < timelineItems.length - 1" class="timeline-line" />
            </div>
            <div class="timeline-content">
              <div class="timeline-top">
                <span class="timeline-time">{{ item.time }}</span>
                <span class="timeline-status" :class="`timeline-status--${item.status.type}`">
                  {{ item.status.label }}
                </span>
              </div>
              <div class="timeline-card-no">{{ item.process_card_no }}</div>
              <div class="timeline-meta">
                <span>{{ item.product_model }}</span>
                <span class="timeline-qty">× {{ formatNumber(item.quantity) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="panel panel-defect">
        <div class="panel-head">
          <span class="panel-title">不良率分析</span>
          <span class="panel-meta">缺陷 {{ formatNumber(data.stats.today_defect_total) }}</span>
        </div>
        <div class="donut-wrap">
          <v-chart class="donut-chart" :option="defectDonutOption" autoresize />
        </div>
        <div class="defect-table-wrap">
          <table class="defect-table">
            <thead>
              <tr>
                <th>缺陷类型</th>
                <th>数量</th>
                <th>占比</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in defectBreakdown" :key="row.type">
                <td>{{ row.type }}</td>
                <td>{{ formatNumber(row.count) }}</td>
                <td>{{ row.ratio }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <el-collapse v-model="collapseActive" class="detail-collapse">
      <el-collapse-item name="detail" title="生产明细">
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
      </el-collapse-item>
    </el-collapse>

    <div v-if="loadError" class="load-error">{{ loadError }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, GraphicComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { fetchProductionOverview } from '../../api/productionOverview'

use([CanvasRenderer, PieChart, TooltipComponent, GraphicComponent])

const loading = ref(true)
const loadError = ref('')
const collapseActive = ref([])

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
  kpi_trends: {},
  stats: { ...defaultStats },
  completion_chart: [],
  detail_rows: [],
}

const data = reactive({ ...defaultData })

const topKpiTiles = computed(() => {
  const kpiTrends = data.kpi_trends || {}
  const statsTrends = data.stats.trends || {}
  const s = data.stats
  const defectTrend = statsTrends.daily_defect_rate
  const defectIsGood = defectTrend?.direction === 'down'

  return [
    {
      key: 'achievement_rate',
      label: '产量达成率',
      displayValue: `${formatGaugeValue(data.achievement_rate)}%`,
      trend: kpiTrends.achievement_rate || statsTrends.achievement_rate,
      trendClass: trendClass(kpiTrends.achievement_rate || statsTrends.achievement_rate, true),
      subLine: `产量面积 ${formatGaugeValue(data.production_area)}`,
      barPercent: Math.min(Math.max(data.achievement_rate, 0), 100),
      accent: 'blue',
    },
    {
      key: 'today_completed',
      label: '今日完成数',
      displayValue: formatNumber(s.today_completed),
      trend: statsTrends.today_completed,
      trendClass: trendClass(statsTrends.today_completed, true),
      subLine: `今日面积产量 ${formatGaugeValue(s.today_area_output)}`,
      accent: 'green',
    },
    {
      key: 'daily_defect_rate',
      label: '日不良率',
      displayValue: s.daily_defect_rate,
      statusTag: {
        label: defectIsGood ? '正常' : '偏高',
        class: defectIsGood ? 'kpi-status-tag--good' : 'kpi-status-tag--bad',
      },
      accent: 'orange',
    },
    {
      key: 'today_incoming_boards',
      label: '今日来板数',
      displayValue: formatNumber(s.today_incoming_boards),
      trend: statsTrends.today_incoming_boards,
      trendClass: trendClass(statsTrends.today_incoming_boards, true),
      accent: 'purple',
    },
  ]
})

const timelineItems = computed(() =>
  data.detail_rows.slice(0, 8).map((row) => ({
    ...row,
    status: resolveRowStatus(row),
  })),
)

const defectBreakdown = computed(() => {
  const total = data.stats.today_defect_total || 0
  if (total === 0) return []
  const weights = [
    { type: '表面划痕', weight: 0.28 },
    { type: '尺寸偏差', weight: 0.22 },
    { type: '色差', weight: 0.18 },
    { type: '气泡', weight: 0.17 },
    { type: '其他', weight: 0.15 },
  ]
  return weights.map(({ type, weight }) => ({
    type,
    count: Math.round(total * weight),
    ratio: `${(weight * 100).toFixed(1)}%`,
  }))
})

const defectDonutOption = computed(() => {
  const rateStr = data.stats.daily_defect_rate || '0%'
  const defectRate = parseFloat(String(rateStr).replace('%', '')) || 0
  const goodRate = Math.max(100 - defectRate, 0)

  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(48, 49, 51, 0.92)',
      borderColor: 'rgba(91, 127, 165, 0.4)',
      textStyle: { color: '#ecf0f1', fontSize: 12 },
      formatter: '{b}: {c}%',
    },
    graphic: [
      {
        type: 'text',
        left: 'center',
        top: '42%',
        style: {
          text: rateStr,
          fill: '#303133',
          fontSize: 22,
          fontWeight: 700,
          textAlign: 'center',
        },
      },
      {
        type: 'text',
        left: 'center',
        top: '54%',
        style: {
          text: '日不良率',
          fill: '#909399',
          fontSize: 11,
          textAlign: 'center',
        },
      },
    ],
    series: [
      {
        type: 'pie',
        radius: ['52%', '72%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: false,
        label: { show: false },
        labelLine: { show: false },
        data: [
          { value: goodRate, name: '良品率', itemStyle: { color: '#e4e7ed' } },
          { value: defectRate, name: '不良率', itemStyle: { color: '#5b7fa5' } },
        ],
      },
    ],
  }
})

function trendClass(trend, upIsGood = false) {
  if (!trend) return ''
  const isUp = trend.direction === 'up'
  const positive = upIsGood ? isUp : !isUp
  return positive ? 'kpi-tile-trend--up' : 'kpi-tile-trend--down'
}

function resolveRowStatus(row) {
  if (row.today_completed >= row.quantity) {
    return { label: '已完成', type: 'done' }
  }
  if (row.today_completed > 0) {
    return { label: '进行中', type: 'active' }
  }
  return { label: '待开始', type: 'pending' }
}

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
    kpi_trends: resp.kpi_trends || {},
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
  background: #f0f2f5;
  color: #303133;
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
  background: #ffffff;
  border: 1px solid #e4e7ed;
  border-left-width: 4px;
  border-radius: 4px;
  padding: 12px 14px 10px;
  min-width: 0;
}

.kpi-tile--blue { border-left-color: #409eff; }
.kpi-tile--green { border-left-color: #67c23a; }
.kpi-tile--orange { border-left-color: #e6a23c; }
.kpi-tile--purple { border-left-color: #9b59b6; }

.kpi-tile-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.kpi-tile-main {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}

.kpi-tile-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.kpi-tile-sub {
  margin-top: 4px;
  font-size: 11px;
  color: #909399;
}

.kpi-tile-trend {
  font-size: 12px;
  font-weight: 500;
}

.kpi-tile-trend--up { color: #67c23a; }
.kpi-tile-trend--down { color: #f56c6c; }

.kpi-status-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
}

.kpi-status-tag--good {
  color: #67c23a;
  background: rgba(103, 194, 58, 0.1);
}

.kpi-status-tag--bad {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.1);
}

.kpi-tile-bar {
  margin-top: 8px;
  height: 3px;
  background: #ebeef5;
  border-radius: 2px;
  overflow: hidden;
}

.kpi-tile-bar-fill {
  height: 100%;
  background: #409eff;
  border-radius: 2px;
  transition: width 0.6s ease;
}

.main-body {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
  gap: 10px;
  flex: 1;
  min-height: 0;
  min-width: 0;
}

.panel {
  background: #ffffff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px 8px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.panel-meta {
  font-size: 11px;
  font-weight: 400;
  color: #909399;
}

.panel-timeline {
  min-height: 320px;
}

.timeline-wrap {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 14px 12px;
}

.timeline-item {
  display: flex;
  gap: 10px;
  min-width: 0;
}

.timeline-axis {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  width: 12px;
  padding-top: 4px;
}

.timeline-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.timeline-dot--done { background: #67c23a; }
.timeline-dot--active { background: #409eff; }
.timeline-dot--pending { background: #c0c4cc; }

.timeline-line {
  flex: 1;
  width: 1px;
  min-height: 24px;
  background: #e4e7ed;
  margin: 4px 0;
}

.timeline-content {
  flex: 1;
  min-width: 0;
  padding-bottom: 14px;
}

.timeline-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 2px;
}

.timeline-time {
  font-size: 11px;
  color: #909399;
  font-variant-numeric: tabular-nums;
}

.timeline-status {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}

.timeline-status--done {
  color: #67c23a;
  background: rgba(103, 194, 58, 0.1);
}

.timeline-status--active {
  color: #409eff;
  background: rgba(64, 158, 255, 0.1);
}

.timeline-status--pending {
  color: #909399;
  background: #f4f4f5;
}

.timeline-card-no {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-meta {
  margin-top: 2px;
  font-size: 11px;
  color: #606266;
  display: flex;
  gap: 6px;
  align-items: center;
}

.timeline-qty {
  color: #909399;
}

.panel-defect {
  min-height: 320px;
}

.donut-wrap {
  flex-shrink: 0;
  height: 180px;
  min-width: 0;
  padding: 4px 8px 0;
}

.donut-chart {
  width: 100%;
  height: 100%;
  min-width: 0;
}

.defect-table-wrap {
  flex: 1;
  min-height: 0;
  overflow-x: auto;
  overflow-y: auto;
  padding: 0 14px 12px;
}

.defect-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
  min-width: 200px;
}

.defect-table th {
  text-align: left;
  color: #909399;
  font-weight: 600;
  padding: 4px 6px;
  border-bottom: 1px solid #ebeef5;
}

.defect-table td {
  color: #606266;
  padding: 5px 6px;
  border-bottom: 1px solid #f2f3f5;
}

.defect-table td:nth-child(2),
.defect-table td:nth-child(3),
.defect-table th:nth-child(2),
.defect-table th:nth-child(3) {
  text-align: right;
}

.detail-collapse {
  flex-shrink: 0;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
  background: #ffffff;
}

.detail-collapse :deep(.el-collapse-item__header) {
  padding: 0 14px;
  height: 40px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  background: #ffffff;
  border-bottom: none;
}

.detail-collapse :deep(.el-collapse-item__wrap) {
  border-top: 1px solid #ebeef5;
}

.detail-collapse :deep(.el-collapse-item__content) {
  padding: 0;
}

.table-wrap {
  overflow-x: auto;
  overflow-y: auto;
  max-height: 280px;
  padding: 0 6px 6px;
  min-width: 0;
}

.compact-table {
  width: 100%;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: #fafafa;
  --el-table-row-hover-bg-color: #f5f7fa;
  --el-table-border-color: #ebeef5;
  --el-table-text-color: #606266;
  --el-table-header-text-color: #909399;
}

.compact-table :deep(.el-table__inner-wrapper)::before {
  display: none;
}

.compact-table :deep(th.el-table__cell) {
  background: #fafafa !important;
  color: #909399 !important;
  font-weight: 600;
  font-size: 11px;
  padding: 6px 0;
  border-bottom: 1px solid #ebeef5 !important;
}

.compact-table :deep(td.el-table__cell) {
  background: transparent !important;
  color: #606266 !important;
  font-size: 11px;
  padding: 5px 0;
  border-bottom: 1px solid #f2f3f5 !important;
}

.compact-table :deep(.compact-row:hover > td.el-table__cell) {
  background: #f5f7fa !important;
}

.load-error {
  text-align: center;
  color: #f56c6c;
  padding: 10px;
  font-size: 13px;
}

@media (max-width: 1100px) {
  .kpi-banner {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .main-body {
    grid-template-columns: 1fr;
  }
}
</style>
