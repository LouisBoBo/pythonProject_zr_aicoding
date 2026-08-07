<template>
  <div class="dashboard-home">
    <!-- 顶部数据行 -->
    <el-row :gutter="16" class="top-stats-row">
      <el-col v-for="item in topStats" :key="item.key" :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">{{ item.label }}</div>
          <div class="stat-value">{{ item.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 主图表区 + 右侧卡片 -->
    <el-row :gutter="16" class="main-row">
      <el-col :xs="24" :lg="16">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">产量趋势图</span>
              <span class="card-subtitle">{{ hourlyTrendDate }}</span>
            </div>
          </template>
          <v-chart class="hourly-chart" :option="hourlyLineOption" autoresize />
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8" class="right-column">
        <el-card shadow="never" class="summary-card monthly-card">
          <div class="summary-label">月产量</div>
          <div class="summary-main">{{ formatNumber(monthlyOutput.value) }}</div>
          <div class="summary-sub">上一月产量：{{ formatNumber(monthlyOutput.lastMonth) }}</div>
        </el-card>

        <el-card shadow="never" class="summary-card daily-card">
          <div class="summary-label">日产量</div>
          <div class="daily-progress-row">
            <span class="daily-current">{{ dailyOutput.current }}</span>
            <span class="daily-sep">/</span>
            <span class="daily-target">{{ dailyOutput.target }}</span>
          </div>
          <el-progress
            :percentage="dailyOutput.percent"
            :stroke-width="10"
            :color="progressColor"
          />
          <div class="daily-percent-text">完成 {{ dailyOutput.percent }}%</div>
        </el-card>

        <el-card shadow="never" class="summary-card efficiency-card">
          <div class="summary-label">效率趋势</div>
          <div class="efficiency-row">
            <div class="efficiency-count">
              <span class="efficiency-num">{{ efficiencyTrend.count }}</span>
              <span class="efficiency-unit">数量</span>
            </div>
            <div class="efficiency-rate">
              <span class="efficiency-num">{{ efficiencyTrend.rate }}%</span>
              <span class="efficiency-unit">比例</span>
            </div>
          </div>
        </el-card>

        <el-card shadow="never" class="chart-card pie-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">异常分析</span>
              <span class="card-highlight">{{ anomalyAnalysis.mainPercent }}%</span>
            </div>
          </template>
          <v-chart class="pie-chart" :option="anomalyPieOption" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <!-- 底部双柱状图 -->
    <el-row :gutter="16" class="bar-row">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span class="card-title">产线产量对比</span>
          </template>
          <v-chart class="bar-chart" :option="lineOutputBarOption" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span class="card-title">不良品类分布</span>
          </template>
          <v-chart class="bar-chart" :option="defectBarOption" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <!-- 生产明细表格 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">生产明细</span>
          <span class="card-subtitle">详细信息</span>
        </div>
      </template>
      <el-table
        :data="pagedTableData"
        stripe
        style="width: 100%"
        @sort-change="handleSortChange"
      >
        <el-table-column prop="line" label="产线" width="100" sortable="custom" />
        <el-table-column prop="product" label="产品" min-width="140" sortable="custom" />
        <el-table-column prop="batchNo" label="批次号" width="130" sortable="custom" />
        <el-table-column prop="planQty" label="计划产量" width="110" sortable="custom" align="right" />
        <el-table-column prop="actualQty" label="实际产量" width="110" sortable="custom" align="right" />
        <el-table-column prop="defectQty" label="不良数" width="90" sortable="custom" align="right" />
        <el-table-column prop="efficiency" label="效率" width="90" sortable="custom" align="right">
          <template #default="{ row }">{{ row.efficiency }}%</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updateTime" label="更新时间" width="160" sortable="custom" />
      </el-table>
      <div class="table-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[5, 10, 20]"
          :total="sortedTableData.length"
          layout="total, sizes, prev, pager, next, jumper"
          background
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart, BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
])

const progressColor = [
  { color: '#667eea', percentage: 100 },
]

const topStats = [
  { key: 'current_time', label: '当前生产时间', value: '7:08' },
  { key: 'today_output', label: '当日产量', value: '525' },
  { key: 'daily_avg', label: '日平均产量', value: '354' },
  { key: 'recent_12h_avg', label: '最近12小时平均产量', value: '20.45' },
]

const hourlyTrendDate = '2022.12.30'

const hourlyProduction = [
  { hour: '00:00', output: 12 },
  { hour: '01:00', output: 8 },
  { hour: '02:00', output: 5 },
  { hour: '03:00', output: 6 },
  { hour: '04:00', output: 10 },
  { hour: '05:00', output: 18 },
  { hour: '06:00', output: 25 },
  { hour: '07:00', output: 32 },
  { hour: '08:00', output: 45 },
  { hour: '09:00', output: 52 },
  { hour: '10:00', output: 48 },
  { hour: '11:00', output: 55 },
  { hour: '12:00', output: 42 },
  { hour: '13:00', output: 38 },
  { hour: '14:00', output: 50 },
  { hour: '15:00', output: 58 },
  { hour: '16:00', output: 62 },
  { hour: '17:00', output: 54 },
  { hour: '18:00', output: 40 },
  { hour: '19:00', output: 28 },
  { hour: '20:00', output: 22 },
  { hour: '21:00', output: 18 },
  { hour: '22:00', output: 15 },
  { hour: '23:00', output: 10 },
]

const monthlyOutput = { value: 3535, lastMonth: 4590 }

const dailyOutput = computed(() => {
  const current = 1810
  const target = 2500
  return {
    current,
    target,
    percent: Math.round((current / target) * 100),
  }
})

const efficiencyTrend = { count: 197, rate: 85 }

const anomalyAnalysis = {
  mainPercent: 81,
  items: [
    { name: '设备异常', value: 81 },
    { name: '品质异常', value: 12 },
    { name: '物料异常', value: 5 },
    { name: '其他', value: 2 },
  ],
}

const lineOutputData = [
  { name: '产线A', value: 820 },
  { name: '产线B', value: 650 },
  { name: '产线C', value: 540 },
  { name: '产线D', value: 480 },
  { name: '产线E', value: 390 },
]

const defectCategoryData = [
  { name: '外观', value: 45 },
  { name: '尺寸', value: 32 },
  { name: '功能', value: 28 },
  { name: '包装', value: 18 },
  { name: '其他', value: 12 },
]

const productionDetails = [
  { line: '产线A', product: '精密零件-X1', batchNo: 'B2022123001', planQty: 500, actualQty: 485, defectQty: 8, efficiency: 97, status: '生产中', updateTime: '2022-12-30 07:05:00' },
  { line: '产线B', product: '外壳组件-Y2', batchNo: 'B2022123002', planQty: 400, actualQty: 392, defectQty: 5, efficiency: 98, status: '生产中', updateTime: '2022-12-30 07:02:00' },
  { line: '产线C', product: '电路板-Z3', batchNo: 'B2022123003', planQty: 350, actualQty: 310, defectQty: 12, efficiency: 89, status: '异常', updateTime: '2022-12-30 06:58:00' },
  { line: '产线D', product: '连接器-M4', batchNo: 'B2022123004', planQty: 300, actualQty: 298, defectQty: 2, efficiency: 99, status: '已完成', updateTime: '2022-12-30 06:45:00' },
  { line: '产线E', product: '传感器-S5', batchNo: 'B2022123005', planQty: 280, actualQty: 265, defectQty: 6, efficiency: 95, status: '生产中', updateTime: '2022-12-30 06:30:00' },
  { line: '产线A', product: '精密零件-X2', batchNo: 'B2022123006', planQty: 450, actualQty: 420, defectQty: 10, efficiency: 93, status: '生产中', updateTime: '2022-12-30 06:15:00' },
  { line: '产线B', product: '外壳组件-Y3', batchNo: 'B2022123007', planQty: 380, actualQty: 375, defectQty: 4, efficiency: 99, status: '已完成', updateTime: '2022-12-30 06:00:00' },
  { line: '产线C', product: '电路板-Z4', batchNo: 'B2022123008', planQty: 320, actualQty: 280, defectQty: 15, efficiency: 88, status: '异常', updateTime: '2022-12-30 05:45:00' },
  { line: '产线D', product: '连接器-M5', batchNo: 'B2022123009', planQty: 260, actualQty: 255, defectQty: 3, efficiency: 98, status: '已完成', updateTime: '2022-12-30 05:30:00' },
  { line: '产线E', product: '传感器-S6', batchNo: 'B2022123010', planQty: 240, actualQty: 230, defectQty: 5, efficiency: 96, status: '生产中', updateTime: '2022-12-30 05:15:00' },
  { line: '产线A', product: '精密零件-X3', batchNo: 'B2022123011', planQty: 420, actualQty: 400, defectQty: 7, efficiency: 95, status: '生产中', updateTime: '2022-12-30 05:00:00' },
  { line: '产线B', product: '外壳组件-Y4', batchNo: 'B2022123012', planQty: 360, actualQty: 350, defectQty: 6, efficiency: 97, status: '已完成', updateTime: '2022-12-30 04:45:00' },
]

const currentPage = ref(1)
const pageSize = ref(5)
const sortProp = ref('')
const sortOrder = ref('')

const chartColors = {
  primary: '#667eea',
  secondary: '#764ba2',
  palette: ['#667eea', '#764ba2', '#48bb78', '#ed8936', '#4299e1'],
}

const hourlyLineOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 48, right: 24, top: 32, bottom: 36 },
  xAxis: {
    type: 'category',
    data: hourlyProduction.map((p) => p.hour),
    axisLine: { lineStyle: { color: '#e0e0e0' } },
    axisLabel: { color: '#888', fontSize: 11 },
  },
  yAxis: {
    type: 'value',
    name: '产量',
    nameTextStyle: { color: '#888', fontSize: 12 },
    axisLine: { show: false },
    splitLine: { lineStyle: { color: '#f0f0f0' } },
    axisLabel: { color: '#888' },
  },
  series: [
    {
      name: '小时产量',
      type: 'line',
      smooth: true,
      data: hourlyProduction.map((p) => p.output),
      lineStyle: { color: chartColors.primary, width: 2.5 },
      itemStyle: { color: chartColors.primary },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(102, 126, 234, 0.3)' },
            { offset: 1, color: 'rgba(102, 126, 234, 0.02)' },
          ],
        },
      },
    },
  ],
}))

const anomalyPieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: {
    orient: 'vertical',
    right: 8,
    top: 'center',
    textStyle: { color: '#666', fontSize: 12 },
  },
  color: chartColors.palette,
  series: [
    {
      name: '异常分析',
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['38%', '50%'],
      avoidLabelOverlap: true,
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' },
      },
      data: anomalyAnalysis.items,
    },
  ],
}))

function buildBarOption(categories, values, color) {
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 48, right: 24, top: 24, bottom: 32 },
    xAxis: {
      type: 'category',
      data: categories,
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisLabel: { color: '#888' },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      axisLabel: { color: '#888' },
    },
    series: [
      {
        type: 'bar',
        data: values,
        barWidth: '45%',
        itemStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color },
              { offset: 1, color: chartColors.secondary },
            ],
          },
          borderRadius: [4, 4, 0, 0],
        },
      },
    ],
  }
}

const lineOutputBarOption = computed(() =>
  buildBarOption(
    lineOutputData.map((d) => d.name),
    lineOutputData.map((d) => d.value),
    chartColors.primary,
  ),
)

const defectBarOption = computed(() =>
  buildBarOption(
    defectCategoryData.map((d) => d.name),
    defectCategoryData.map((d) => d.value),
    '#48bb78',
  ),
)

const sortedTableData = computed(() => {
  const data = [...productionDetails]
  if (!sortProp.value || !sortOrder.value) return data

  const prop = sortProp.value
  const asc = sortOrder.value === 'ascending'

  return data.sort((a, b) => {
    const va = a[prop]
    const vb = b[prop]
    if (typeof va === 'number' && typeof vb === 'number') {
      return asc ? va - vb : vb - va
    }
    return asc
      ? String(va).localeCompare(String(vb), 'zh-CN')
      : String(vb).localeCompare(String(va), 'zh-CN')
  })
})

const pagedTableData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return sortedTableData.value.slice(start, start + pageSize.value)
})

function formatNumber(num) {
  return num.toLocaleString('zh-CN')
}

function statusTagType(status) {
  if (status === '异常') return 'danger'
  if (status === '已完成') return 'success'
  return 'primary'
}

function handleSortChange({ prop, order }) {
  sortProp.value = prop || ''
  sortOrder.value = order || ''
  currentPage.value = 1
}
</script>

<style scoped>
.dashboard-home {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.top-stats-row {
  margin-bottom: 16px;
}

.stat-card {
  text-align: center;
  border: none;
}

.stat-card :deep(.el-card__body) {
  padding: 18px 16px;
}

.stat-label {
  font-size: 13px;
  color: #888;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
}

.main-row {
  margin-bottom: 16px;
}

.right-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chart-card {
  border: none;
  height: 100%;
}

.chart-card :deep(.el-card__header) {
  padding: 14px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.chart-card :deep(.el-card__body) {
  padding: 12px 16px 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.card-subtitle {
  font-size: 12px;
  color: #999;
}

.card-highlight {
  font-size: 18px;
  font-weight: 700;
  color: #667eea;
}

.hourly-chart {
  height: 360px;
  width: 100%;
}

.summary-card {
  border: none;
}

.summary-card :deep(.el-card__body) {
  padding: 16px 20px;
}

.summary-label {
  font-size: 13px;
  color: #888;
  margin-bottom: 8px;
}

.summary-main {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
}

.summary-sub {
  margin-top: 6px;
  font-size: 12px;
  color: #999;
}

.daily-progress-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 10px;
}

.daily-current {
  font-size: 28px;
  font-weight: 700;
  color: #667eea;
}

.daily-sep {
  font-size: 18px;
  color: #ccc;
}

.daily-target {
  font-size: 18px;
  color: #888;
}

.daily-percent-text {
  margin-top: 6px;
  font-size: 12px;
  color: #888;
  text-align: right;
}

.efficiency-row {
  display: flex;
  justify-content: space-around;
  padding-top: 4px;
}

.efficiency-count,
.efficiency-rate {
  text-align: center;
}

.efficiency-num {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
}

.efficiency-unit {
  font-size: 12px;
  color: #999;
}

.pie-card :deep(.el-card__body) {
  padding: 0 8px 8px;
}

.pie-chart {
  height: 180px;
  width: 100%;
}

.bar-row {
  margin-bottom: 16px;
}

.bar-chart {
  height: 260px;
  width: 100%;
}

.table-card {
  border: none;
}

.table-card :deep(.el-card__header) {
  padding: 14px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 1200px) {
  .hourly-chart {
    height: 300px;
  }

  .right-column {
    margin-top: 16px;
  }
}

@media (max-width: 768px) {
  .stat-value {
    font-size: 22px;
  }

  .hourly-chart {
    height: 260px;
  }

  .bar-chart {
    height: 220px;
  }
}
</style>
