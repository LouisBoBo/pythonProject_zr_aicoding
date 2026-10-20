<template>
  <div class="downtime-report-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="停机日期">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            clearable
            style="width: 260px"
          />
        </el-form-item>
        <el-form-item label="车间">
          <el-select
            v-model="filters.workshop"
            placeholder="全部"
            clearable
            filterable
            style="width: 140px"
          >
            <el-option v-for="ws in filterOptions.workshops" :key="ws" :label="ws" :value="ws" />
          </el-select>
        </el-form-item>
        <el-form-item label="设备">
          <el-select
            v-model="filters.equipmentId"
            placeholder="全部"
            clearable
            filterable
            style="width: 200px"
          >
            <el-option
              v-for="eq in equipmentOptions"
              :key="eq.id"
              :label="`${eq.name}（${eq.equipment_code}）`"
              :value="eq.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="停机原因">
          <el-select
            v-model="filters.downtimeReason"
            placeholder="全部"
            clearable
            style="width: 140px"
          >
            <el-option
              v-for="reason in filterOptions.downtime_reasons"
              :key="reason"
              :label="reason"
              :value="reason"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div class="metric-cards">
      <el-card v-for="card in metricCards" :key="card.key" shadow="never" class="metric-card">
        <div class="metric-label">{{ card.label }}</div>
        <div class="metric-value" :class="{ highlight: card.highlight }">
          {{ card.value }}<span v-if="card.unit" class="metric-unit">{{ card.unit }}</span>
        </div>
      </el-card>
    </div>

    <el-card shadow="never" class="chart-card">
      <div class="section-title">停机趋势（按日）</div>
      <VChart v-if="hasTrendData" class="trend-chart" :option="trendChartOption" autoresize />
      <el-empty v-else description="所选条件下暂无停机趋势" :image-size="80" />
    </el-card>

    <div class="chart-row">
      <el-card shadow="never" class="chart-card chart-half">
        <div class="section-title">停机原因分布</div>
        <VChart v-if="byReason.length" class="sub-chart" :option="reasonChartOption" autoresize />
        <el-empty v-else description="暂无原因分布数据" :image-size="72" />
      </el-card>
      <el-card shadow="never" class="chart-card chart-half">
        <div class="section-title">车间停机对比</div>
        <VChart v-if="byWorkshop.length" class="sub-chart" :option="workshopChartOption" autoresize />
        <el-empty v-else description="暂无车间对比数据" :image-size="72" />
      </el-card>
    </div>

    <el-card shadow="never" class="chart-card">
      <div class="section-title">停机时长 Top 设备</div>
      <VChart
        v-if="topEquipment.length"
        class="rank-chart"
        :style="{ height: rankChartHeight + 'px' }"
        :option="equipmentChartOption"
        autoresize
      />
      <el-empty v-else description="暂无设备排名数据" :image-size="80" />
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <span class="table-title">停机明细</span>
          <el-tag size="small" type="info">运行日志 · 停机时段</el-tag>
          <el-tag size="small" effect="plain">共 {{ total }} 条</el-tag>
        </div>
        <div class="toolbar-right">
          <el-button :icon="Download" :loading="exporting" @click="handleExport">导出 Excel</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column label="设备" min-width="160">
          <template #default="{ row }">
            <div class="cell-device">
              <span class="device-name">{{ row.equipment_name }}</span>
              <span class="device-code">{{ row.equipment_code }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="workshop" label="车间" width="100">
          <template #default="{ row }">{{ row.workshop || '—' }}</template>
        </el-table-column>
        <el-table-column label="停机开始" width="170">
          <template #default="{ row }">{{ formatDateTime(row.start_at) }}</template>
        </el-table-column>
        <el-table-column label="停机结束" width="170">
          <template #default="{ row }">{{ row.end_at ? formatDateTime(row.end_at) : '—' }}</template>
        </el-table-column>
        <el-table-column label="时长(h)" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.duration_hours) }}</template>
        </el-table-column>
        <el-table-column prop="downtime_reason" label="停机原因" min-width="120">
          <template #default="{ row }">{{ row.downtime_reason || '—' }}</template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="loadReport"
          @current-change="loadReport"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import {
  exportEquipmentDowntimeReport,
  fetchEquipmentDowntimeFilters,
  fetchEquipmentDowntimeReport,
} from '../../api/reports/equipmentDowntime.js'

use([CanvasRenderer, LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const REASON_COLORS = ['#409EFF', '#F56C6C', '#E6A23C', '#67C23A', '#909399', '#626aef']

function defaultDateRange() {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 6)
  const fmt = (d) => {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }
  return [fmt(start), fmt(end)]
}

const loading = ref(false)
const exporting = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const dateRange = ref(defaultDateRange())
const trend = ref([])
const byReason = ref([])
const byWorkshop = ref([])
const topEquipment = ref([])

const summary = reactive({
  event_count: 0,
  total_duration_hours: 0,
  avg_duration_hours: 0,
  equipment_count: 0,
})

const filterOptions = reactive({
  workshops: [],
  downtime_reasons: [],
  equipment: [],
})

const filters = reactive({
  workshop: '',
  equipmentId: null,
  downtimeReason: '',
})

const equipmentOptions = computed(() => {
  if (!filters.workshop) return filterOptions.equipment
  return filterOptions.equipment.filter((eq) => eq.workshop === filters.workshop)
})

const metricCards = computed(() => [
  {
    key: 'events',
    label: '停机次数',
    value: summary.event_count,
    highlight: true,
  },
  {
    key: 'total',
    label: '停机时长合计',
    value: formatHours(summary.total_duration_hours),
    unit: 'h',
  },
  {
    key: 'avg',
    label: '单次平均时长',
    value: formatHours(summary.avg_duration_hours),
    unit: 'h',
  },
  {
    key: 'equip',
    label: '涉及设备',
    value: summary.equipment_count,
    unit: '台',
  },
])

const hasTrendData = computed(() =>
  trend.value.some((p) => p.event_count > 0 || p.duration_hours > 0),
)

const rankChartHeight = computed(() =>
  Math.max(240, topEquipment.value.length * 36 + 48),
)

const trendChartOption = computed(() => {
  const dates = trend.value.map((p) => p.period_date)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['停机次数', '停机时长'], bottom: 0 },
    grid: { left: 48, right: 48, top: 28, bottom: 48 },
    xAxis: { type: 'category', data: dates },
    yAxis: [
      { type: 'value', name: '次数', minInterval: 1 },
      { type: 'value', name: '时长(h)', splitLine: { show: false } },
    ],
    series: [
      {
        name: '停机次数',
        type: 'bar',
        data: trend.value.map((p) => p.event_count),
        itemStyle: { color: '#409EFF' },
        barMaxWidth: 28,
      },
      {
        name: '停机时长',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        showSymbol: true,
        data: trend.value.map((p) => p.duration_hours),
        itemStyle: { color: '#E6A23C' },
      },
    ],
  }
})

const reasonChartOption = computed(() => ({
  color: REASON_COLORS,
  tooltip: {
    trigger: 'item',
    formatter: '{b}<br/>时长 {c} h（{d}%）',
  },
  legend: { type: 'scroll', bottom: 0 },
  series: [
    {
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '46%'],
      avoidLabelOverlap: true,
      label: { formatter: '{b}\n{c}h' },
      data: byReason.value.map((row) => ({
        name: row.label,
        value: row.duration_hours,
      })),
    },
  ],
}))

const workshopChartOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  legend: { data: ['停机次数', '停机时长'], bottom: 0 },
  grid: { left: 48, right: 24, top: 24, bottom: 48 },
  xAxis: {
    type: 'category',
    data: byWorkshop.value.map((row) => row.label),
    axisLabel: { interval: 0, rotate: byWorkshop.value.length > 4 ? 24 : 0 },
  },
  yAxis: [
    { type: 'value', name: '次数', minInterval: 1 },
    { type: 'value', name: '时长(h)', splitLine: { show: false } },
  ],
  series: [
    {
      name: '停机次数',
      type: 'bar',
      data: byWorkshop.value.map((row) => row.event_count),
      itemStyle: { color: '#67C23A' },
      barMaxWidth: 32,
    },
    {
      name: '停机时长',
      type: 'line',
      yAxisIndex: 1,
      smooth: true,
      data: byWorkshop.value.map((row) => row.duration_hours),
      itemStyle: { color: '#F56C6C' },
    },
  ],
}))

const equipmentChartOption = computed(() => {
  const labels = topEquipment.value.map(
    (row) => `${row.equipment_name}（${row.equipment_code}）`,
  )
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const p = params[0]
        const row = topEquipment.value[p.dataIndex]
        if (!row) return ''
        return `${row.equipment_name}<br/>编码 ${row.equipment_code}<br/>停机 ${row.event_count} 次 · ${row.duration_hours} h`
      },
    },
    grid: { left: 160, right: 24, top: 16, bottom: 24 },
    xAxis: { type: 'value', name: '时长(h)' },
    yAxis: {
      type: 'category',
      data: labels,
      inverse: true,
      axisLabel: { width: 140, overflow: 'truncate' },
    },
    series: [
      {
        type: 'bar',
        data: topEquipment.value.map((row) => row.duration_hours),
        itemStyle: { color: '#409EFF' },
        barMaxWidth: 22,
      },
    ],
  }
})

watch(
  () => filters.workshop,
  () => {
    if (!filters.equipmentId) return
    const selected = filterOptions.equipment.find((eq) => eq.id === filters.equipmentId)
    if (selected && filters.workshop && selected.workshop !== filters.workshop) {
      filters.equipmentId = null
    }
  },
)

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
}

function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  const s = String(d.getSeconds()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}:${s}`
}

function applyAnalytics(data) {
  trend.value = data?.trend || []
  byReason.value = data?.by_reason || []
  byWorkshop.value = data?.by_workshop || []
  topEquipment.value = data?.top_equipment || []
  summary.event_count = data?.summary?.event_count ?? 0
  summary.total_duration_hours = data?.summary?.total_duration_hours ?? 0
  summary.avg_duration_hours = data?.summary?.avg_duration_hours ?? 0
  summary.equipment_count = data?.summary?.equipment_count ?? 0
}

async function loadFilters() {
  try {
    const data = await fetchEquipmentDowntimeFilters()
    filterOptions.workshops = data.workshops || []
    filterOptions.downtime_reasons = data.downtime_reasons || []
    filterOptions.equipment = data.equipment || []
  } catch (err) {
    ElMessage.error(err.message || '加载筛选选项失败')
  }
}

async function loadReport() {
  loading.value = true
  try {
    const [dateFrom, dateTo] = dateRange.value || []
    const data = await fetchEquipmentDowntimeReport({
      page: page.value,
      pageSize: pageSize.value,
      dateFrom,
      dateTo,
      workshop: filters.workshop || undefined,
      equipmentId: filters.equipmentId || undefined,
      downtimeReason: filters.downtimeReason || undefined,
    })
    items.value = data.items || []
    total.value = data.total || 0
    applyAnalytics(data)
  } catch (err) {
    items.value = []
    total.value = 0
    applyAnalytics({})
    ElMessage.error(err.message || '加载设备停机报表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadReport()
}

function handleReset() {
  dateRange.value = defaultDateRange()
  filters.workshop = ''
  filters.equipmentId = null
  filters.downtimeReason = ''
  page.value = 1
  loadReport()
}

async function handleExport() {
  exporting.value = true
  try {
    const [dateFrom, dateTo] = dateRange.value || []
    const blob = await exportEquipmentDowntimeReport({
      dateFrom,
      dateTo,
      workshop: filters.workshop || undefined,
      equipmentId: filters.equipmentId || undefined,
      downtimeReason: filters.downtimeReason || undefined,
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `设备停机报表_${new Date().toISOString().slice(0, 10)}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (err) {
    ElMessage.error(err.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  await loadFilters()
  await loadReport()
})
</script>

<style scoped>
.downtime-report-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-card,
.chart-card,
.table-card {
  border-radius: 8px;
}

.search-form {
  flex-wrap: wrap;
}

.metric-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}

.metric-card {
  border-radius: 8px;
}

.metric-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.metric-value {
  font-size: 22px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.metric-value.highlight {
  color: var(--el-color-primary);
}

.metric-unit {
  font-size: 14px;
  font-weight: normal;
  margin-left: 4px;
  color: var(--el-text-color-secondary);
}

.section-title {
  font-weight: 600;
  font-size: 15px;
  margin-bottom: 12px;
}

.trend-chart {
  width: 100%;
  height: 320px;
}

.sub-chart {
  width: 100%;
  height: 280px;
}

.rank-chart {
  width: 100%;
  min-height: 240px;
}

.chart-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.chart-half {
  flex: 1;
  min-width: 280px;
}

.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.table-title {
  font-weight: 600;
  font-size: 15px;
}

.cell-device {
  display: flex;
  flex-direction: column;
  line-height: 1.35;
}

.device-name {
  font-weight: 500;
}

.device-code {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
