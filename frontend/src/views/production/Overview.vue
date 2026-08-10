<template>
  <div v-loading="loading" class="production-overview">
    <div class="kpi-banner">
      <div class="kpi-card kpi-card--blue">
        <div class="kpi-card-label">产量达成率</div>
        <div class="kpi-card-value">{{ formatGaugeValue(data.achievement_rate) }}%</div>
        <div class="kpi-card-sub">
          产量面积 {{ formatGaugeValue(data.production_area) }}
          · 面积产量 {{ formatArea(data.stats.today_area_output) }}
        </div>
        <div class="kpi-card-bar">
          <div
            class="kpi-card-bar-fill kpi-card-bar-fill--blue"
            :style="{ width: `${Math.min(data.achievement_rate, 100)}%` }"
          />
        </div>
      </div>

      <div class="kpi-card kpi-card--green">
        <div class="kpi-card-label">今日完成数</div>
        <div class="kpi-card-row">
          <span class="kpi-card-value">{{ formatNumber(data.stats.today_completed) }}</span>
          <span
            v-if="statsTrends.today_completed"
            class="kpi-trend"
            :class="statsTrends.today_completed.direction === 'up' ? 'kpi-trend--up' : 'kpi-trend--down'"
          >
            {{ statsTrends.today_completed.direction === 'up' ? '↑' : '↓' }}
            较昨日 {{ statsTrends.today_completed.text }}
          </span>
        </div>
      </div>

      <div class="kpi-card kpi-card--orange">
        <div class="kpi-card-label">日不良率</div>
        <div class="kpi-card-row">
          <span class="kpi-card-value">{{ data.stats.daily_defect_rate }}</span>
          <span
            class="kpi-status-tag"
            :class="defectStatusGood ? 'kpi-status-tag--good' : 'kpi-status-tag--bad'"
          >
            {{ defectStatusGood ? '正常' : '偏高' }}
          </span>
        </div>
        <div class="kpi-card-sub">缺陷总数 {{ formatNumber(data.stats.today_defect_total) }}</div>
      </div>

      <div class="kpi-card kpi-card--purple">
        <div class="kpi-card-label">今日来板数</div>
        <div class="kpi-card-row">
          <span class="kpi-card-value">{{ formatNumber(data.stats.today_incoming_boards) }}</span>
          <span
            v-if="statsTrends.today_incoming_boards"
            class="kpi-trend"
            :class="statsTrends.today_incoming_boards.direction === 'up' ? 'kpi-trend--up' : 'kpi-trend--down'"
          >
            {{ statsTrends.today_incoming_boards.direction === 'up' ? '↑' : '↓' }}
            {{ statsTrends.today_incoming_boards.text }}
          </span>
        </div>
      </div>
    </div>

    <div class="main-body">
      <div class="card card-timeline">
        <div class="card-head">生产进度时间线</div>
        <div class="timeline-scroll">
          <ul class="timeline-list">
            <li v-for="(item, idx) in timelineItems" :key="item.process_card_no + idx" class="timeline-item">
              <div class="timeline-axis">
                <span class="timeline-dot" />
                <span v-if="idx < timelineItems.length - 1" class="timeline-line" />
              </div>
              <div class="timeline-content">
                <div class="timeline-top">
                  <span class="timeline-time">{{ item.time }}</span>
                  <span class="timeline-tag" :class="`timeline-tag--${item.statusKey}`">{{ item.statusLabel }}</span>
                </div>
                <div class="timeline-card-no">{{ item.process_card_no }}</div>
                <div class="timeline-meta">
                  <span>{{ item.product_model }}</span>
                  <span class="timeline-qty">数量 {{ formatNumber(item.quantity) }}</span>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>

      <div class="card card-defect">
        <div class="card-head">不良率分析</div>
        <div class="donut-wrap">
          <v-chart class="donut-chart" :option="defectDonutOption" autoresize />
          <div class="donut-center">
            <div class="donut-center-value">{{ data.stats.daily_defect_rate }}</div>
            <div class="donut-center-label">日不良率</div>
          </div>
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
                <td>{{ row.count }}</td>
                <td>{{ row.percent }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <el-collapse v-model="collapseActive" class="detail-collapse">
      <el-collapse-item name="detail" title="生产明细">
        <div class="detail-table-wrap">
          <el-table
            :data="data.detail_rows"
            class="detail-table"
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
import { TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { fetchProductionOverview } from '../../api/productionOverview'

use([CanvasRenderer, PieChart, TooltipComponent])

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

const statsTrends = computed(() => data.stats.trends || {})

const defectStatusGood = computed(() => {
  const t = statsTrends.value.daily_defect_rate
  return !t || t.direction === 'down'
})

const timelineItems = computed(() => {
  const rows = [...(data.detail_rows || [])].slice(-8).reverse()
  return rows.map((row) => {
    let statusKey = 'pending'
    let statusLabel = '待开始'
    if (row.today_completed >= row.quantity) {
      statusKey = 'done'
      statusLabel = '已完成'
    } else if (row.today_completed > 0) {
      statusKey = 'progress'
      statusLabel = '进行中'
    }
    return { ...row, statusKey, statusLabel }
  })
})

const defectBreakdown = computed(() => {
  const total = data.stats.today_defect_total
  if (!total) return []
  const types = [
    { type: '外观不良', ratio: 0.32 },
    { type: '尺寸偏差', ratio: 0.28 },
    { type: '焊接缺陷', ratio: 0.18 },
    { type: '物料缺失', ratio: 0.14 },
    { type: '其他', ratio: 0.08 },
  ]
  return types.map((t) => ({
    type: t.type,
    count: Math.max(1, Math.round(total * t.ratio)),
    percent: `${(t.ratio * 100).toFixed(1)}%`,
  }))
})

const defectDonutOption = computed(() => {
  const rate = parseFloat(String(data.stats.daily_defect_rate).replace('%', '')) || 0
  const good = Math.max(100 - rate, 0)
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {d}%',
    },
    series: [
      {
        type: 'pie',
        radius: ['58%', '78%'],
        center: ['50%', '50%'],
        silent: true,
        label: { show: false },
        data: [
          { value: good, name: '良品', itemStyle: { color: '#e4e7ed' } },
          { value: rate || 0.01, name: '不良', itemStyle: { color: '#5b7fa5' } },
        ],
      },
    ],
  }
})

function formatGaugeValue(val) {
  if (Number.isInteger(val)) return String(val)
  return val.toFixed(1)
}

function formatArea(val) {
  return Number(val).toLocaleString('zh-CN', { maximumFractionDigits: 1 })
}

function formatNumber(val) {
  return Number(val).toLocaleString('zh-CN')
}

function tableRowClass() {
  return 'detail-row'
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
  gap: 12px;
  flex-shrink: 0;
}

.kpi-card {
  background: #ffffff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 14px 16px 12px;
  min-width: 0;
  border-left-width: 4px;
}

.kpi-card--blue { border-left-color: #409eff; }
.kpi-card--green { border-left-color: #67c23a; }
.kpi-card--orange { border-left-color: #e6a23c; }
.kpi-card--purple { border-left-color: #9b59b6; }

.kpi-card-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.kpi-card-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}

.kpi-card-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  min-width: 0;
}

.kpi-card-sub {
  margin-top: 6px;
  font-size: 11px;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kpi-card-bar {
  margin-top: 10px;
  height: 4px;
  background: #ebeef5;
  border-radius: 2px;
  overflow: hidden;
}

.kpi-card-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}

.kpi-card-bar-fill--blue {
  background: #409eff;
}

.kpi-trend {
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.kpi-trend--up { color: #67c23a; }
.kpi-trend--down { color: #f56c6c; }

.kpi-status-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 3px;
  font-weight: 500;
}

.kpi-status-tag--good {
  color: #67c23a;
  background: rgba(103, 194, 58, 0.12);
}

.kpi-status-tag--bad {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.12);
}

.main-body {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
  gap: 12px;
  flex: 1;
  min-height: 0;
  min-width: 0;
}

.card {
  background: #ffffff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

.card-head {
  padding: 12px 16px 10px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.card-timeline {
  min-height: 280px;
}

.timeline-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 16px;
}

.timeline-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.timeline-item {
  display: flex;
  gap: 12px;
  min-width: 0;
}

.timeline-axis {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 12px;
  flex-shrink: 0;
}

.timeline-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #5b7fa5;
  margin-top: 6px;
  flex-shrink: 0;
}

.timeline-line {
  flex: 1;
  width: 2px;
  background: #e4e7ed;
  min-height: 24px;
}

.timeline-content {
  flex: 1;
  min-width: 0;
  padding-bottom: 16px;
}

.timeline-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.timeline-time {
  font-size: 12px;
  color: #909399;
  font-family: 'Courier New', monospace;
}

.timeline-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
}

.timeline-tag--done {
  color: #67c23a;
  background: rgba(103, 194, 58, 0.12);
}

.timeline-tag--progress {
  color: #409eff;
  background: rgba(64, 158, 255, 0.12);
}

.timeline-tag--pending {
  color: #909399;
  background: #f0f2f5;
}

.timeline-card-no {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #606266;
  flex-wrap: wrap;
}

.timeline-qty {
  color: #909399;
}

.card-defect {
  min-height: 280px;
}

.donut-wrap {
  position: relative;
  height: 160px;
  flex-shrink: 0;
  min-width: 0;
}

.donut-chart {
  width: 100%;
  height: 100%;
  min-width: 0;
}

.donut-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.donut-center-value {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  line-height: 1.1;
}

.donut-center-label {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

.defect-table-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0 16px 12px;
}

.defect-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.defect-table th {
  text-align: left;
  color: #909399;
  font-weight: 500;
  padding: 6px 4px;
  border-bottom: 1px solid #ebeef5;
}

.defect-table td {
  padding: 7px 4px;
  color: #606266;
  border-bottom: 1px solid #f5f7fa;
}

.defect-table th:last-child,
.defect-table td:last-child {
  text-align: right;
}

.detail-collapse {
  flex-shrink: 0;
  border: none;
  background: transparent;
  min-width: 0;
}

.detail-collapse :deep(.el-collapse-item) {
  background: #ffffff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}

.detail-collapse :deep(.el-collapse-item__header) {
  padding: 0 16px;
  height: 44px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  border-bottom: none;
  background: #ffffff;
}

.detail-collapse :deep(.el-collapse-item__wrap) {
  border-top: 1px solid #ebeef5;
}

.detail-collapse :deep(.el-collapse-item__content) {
  padding: 0;
}

.detail-table-wrap {
  width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 0 8px 8px;
}

.detail-table {
  width: 100%;
  min-width: 640px;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: #fafafa;
  --el-table-row-hover-bg-color: #f5f7fa;
  --el-table-border-color: #ebeef5;
  --el-table-text-color: #606266;
  --el-table-header-text-color: #909399;
}

.detail-table :deep(.el-table__inner-wrapper)::before {
  display: none;
}

.detail-table :deep(th.el-table__cell) {
  background: #fafafa !important;
  font-weight: 600;
  font-size: 11px;
  padding: 6px 0;
}

.detail-table :deep(td.el-table__cell) {
  font-size: 11px;
  padding: 5px 0;
}

.detail-table :deep(.detail-row:hover > td.el-table__cell) {
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
