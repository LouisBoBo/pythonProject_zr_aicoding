<template>
  <div class="equipment-metrics-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="日期范围">
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
            style="width: 150px"
          >
            <el-option v-for="item in filterOptions.workshops" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="设备类型">
          <el-select
            v-model="filters.equipmentType"
            placeholder="全部"
            clearable
            filterable
            style="width: 150px"
          >
            <el-option
              v-for="item in filterOptions.equipmentTypes"
              :key="item"
              :label="item"
              :value="item"
            />
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
              v-for="eq in filteredEquipmentOptions"
              :key="eq.id"
              :label="`${eq.name}（${eq.equipment_code}）`"
              :value="eq.id"
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
          {{ formatMetric(card.value, card.unit) }}
        </div>
      </el-card>
    </div>

    <el-card shadow="never" class="chart-card">
      <div class="section-title">指标趋势</div>
      <v-chart v-if="trend.length" class="trend-chart" :option="chartOption" autoresize />
      <el-empty v-else description="暂无趋势数据" :image-size="80" />
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <span class="table-title">设备明细</span>
          <el-tag size="small" type="info">共 {{ total }} 条</el-tag>
        </div>
        <div class="toolbar-right">
          <el-button :icon="Download" :loading="exporting" @click="handleExport">导出 Excel</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="period_date" label="日期" width="120" />
        <el-table-column prop="equipment_code" label="设备编号" width="120" />
        <el-table-column prop="equipment_name" label="设备名称" min-width="120" />
        <el-table-column prop="workshop" label="车间" min-width="110">
          <template #default="{ row }">{{ row.workshop || '—' }}</template>
        </el-table-column>
        <el-table-column prop="equipment_type" label="设备类型" min-width="110">
          <template #default="{ row }">{{ row.equipment_type || '—' }}</template>
        </el-table-column>
        <el-table-column prop="oee" label="OEE(%)" width="90" align="right">
          <template #default="{ row }">{{ formatPercent(row.oee) }}</template>
        </el-table-column>
        <el-table-column prop="availability" label="时间稼动率(%)" width="120" align="right">
          <template #default="{ row }">{{ formatPercent(row.availability) }}</template>
        </el-table-column>
        <el-table-column prop="performance" label="性能稼动率(%)" width="120" align="right">
          <template #default="{ row }">{{ formatPercent(row.performance) }}</template>
        </el-table-column>
        <el-table-column prop="quality" label="良率(%)" width="90" align="right">
          <template #default="{ row }">{{ formatPercent(row.quality) }}</template>
        </el-table-column>
        <el-table-column prop="utilization_rate" label="稼动率(%)" width="100" align="right">
          <template #default="{ row }">{{ formatPercent(row.utilization_rate) }}</template>
        </el-table-column>
        <el-table-column prop="uptime_rate" label="开机率(%)" width="100" align="right">
          <template #default="{ row }">{{ formatPercent(row.uptime_rate) }}</template>
        </el-table-column>
        <el-table-column prop="downtime_hours" label="停机时长(h)" width="110" align="right">
          <template #default="{ row }">{{ formatHours(row.downtime_hours) }}</template>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import {
  exportEquipmentMetricsReport,
  fetchEquipmentMetricsFilters,
  fetchEquipmentMetricsReport,
} from '../../api/reports/equipmentMetrics.js'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

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
const trend = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const dateRange = ref(defaultDateRange())
const summary = reactive({
  oee: 0,
  availability: 0,
  performance: 0,
  quality: 0,
  utilization_rate: 0,
  uptime_rate: 0,
  downtime_hours: 0,
})

const filterOptions = reactive({
  workshops: [],
  equipmentTypes: [],
  equipment: [],
})

const filters = reactive({
  workshop: '',
  equipmentType: '',
  equipmentId: null,
})

const dateFrom = computed(() => (dateRange.value && dateRange.value[0]) || '')
const dateTo = computed(() => (dateRange.value && dateRange.value[1]) || '')

const filteredEquipmentOptions = computed(() => {
  let list = filterOptions.equipment || []
  if (filters.workshop) {
    list = list.filter((eq) => eq.department === filters.workshop)
  }
  if (filters.equipmentType) {
    list = list.filter((eq) => eq.spec_model === filters.equipmentType)
  }
  return list
})

const metricCards = computed(() => [
  { key: 'oee', label: 'OEE 综合效率', value: summary.oee, unit: '%', highlight: true },
  { key: 'availability', label: '时间稼动率', value: summary.availability, unit: '%' },
  { key: 'performance', label: '性能稼动率', value: summary.performance, unit: '%' },
  { key: 'quality', label: '良率', value: summary.quality, unit: '%' },
  { key: 'utilization_rate', label: '稼动率', value: summary.utilization_rate, unit: '%' },
  { key: 'uptime_rate', label: '开机率', value: summary.uptime_rate, unit: '%' },
  { key: 'downtime_hours', label: '停机时长', value: summary.downtime_hours, unit: 'h' },
])

const chartOption = computed(() => {
  const dates = trend.value.map((p) => p.period_date)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['OEE', '时间稼动率', '性能稼动率', '良率', '稼动率', '开机率'], bottom: 0 },
    grid: { left: 48, right: 24, top: 24, bottom: 48 },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: { type: 'value', name: '%', min: 0, max: 100 },
    series: [
      { name: 'OEE', type: 'line', smooth: true, data: trend.value.map((p) => p.oee) },
      { name: '时间稼动率', type: 'line', smooth: true, data: trend.value.map((p) => p.availability) },
      { name: '性能稼动率', type: 'line', smooth: true, data: trend.value.map((p) => p.performance) },
      { name: '良率', type: 'line', smooth: true, data: trend.value.map((p) => p.quality) },
      { name: '稼动率', type: 'line', smooth: true, data: trend.value.map((p) => p.utilization_rate) },
      { name: '开机率', type: 'line', smooth: true, data: trend.value.map((p) => p.uptime_rate) },
    ],
  }
})

function formatPercent(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
}

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
}

function formatMetric(value, unit) {
  if (unit === 'h') return formatHours(value)
  return `${formatPercent(value)}${unit}`
}

function buildQueryParams() {
  return {
    page: page.value,
    pageSize: pageSize.value,
    dateFrom: dateFrom.value || undefined,
    dateTo: dateTo.value || undefined,
    workshop: filters.workshop || undefined,
    equipmentType: filters.equipmentType || undefined,
    equipmentId: filters.equipmentId || undefined,
  }
}

function applySummary(data) {
  const s = data?.summary || {}
  summary.oee = s.oee || 0
  summary.availability = s.availability || 0
  summary.performance = s.performance || 0
  summary.quality = s.quality || 0
  summary.utilization_rate = s.utilization_rate || 0
  summary.uptime_rate = s.uptime_rate || 0
  summary.downtime_hours = s.downtime_hours || 0
}

async function loadFilters() {
  try {
    const resp = await fetchEquipmentMetricsFilters()
    filterOptions.workshops = resp.workshops || []
    filterOptions.equipmentTypes = resp.equipment_types || []
    filterOptions.equipment = resp.equipment || []
  } catch {
    filterOptions.workshops = []
    filterOptions.equipmentTypes = []
    filterOptions.equipment = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const resp = await fetchEquipmentMetricsReport(buildQueryParams())
    items.value = resp.items || []
    trend.value = resp.trend || []
    total.value = resp.total || 0
    applySummary(resp)
  } catch (err) {
    ElMessage.error(err.message || '加载报表失败')
    items.value = []
    trend.value = []
    total.value = 0
    applySummary({})
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
  filters.equipmentType = ''
  filters.equipmentId = null
  page.value = 1
  loadReport()
}

async function handleExport() {
  exporting.value = true
  try {
    const { page: _p, pageSize: _s, ...exportParams } = buildQueryParams()
    const blob = await exportEquipmentMetricsReport(exportParams)
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `设备报表_${new Date().toISOString().slice(0, 10)}.xlsx`
    link.click()
    URL.revokeObjectURL(link.href)
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
.equipment-metrics-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.search-card,
.chart-card,
.table-card {
  border-radius: 4px;
}

.search-form {
  margin-bottom: -8px;
}

.metric-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.metric-card {
  border-radius: 4px;
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

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
}

.trend-chart {
  width: 100%;
  height: 320px;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.table-title {
  font-size: 15px;
  font-weight: 600;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
