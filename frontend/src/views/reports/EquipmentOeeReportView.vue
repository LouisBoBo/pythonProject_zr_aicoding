<template>
  <div class="equipment-oee-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="时间范围">
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
            @change="handleWorkshopChange"
          >
            <el-option v-for="w in filterOptions.workshops" :key="w" :label="w" :value="w" />
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
            <el-option v-for="t in filterOptions.equipmentTypes" :key="t" :label="t" :value="t" />
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
        <div class="metric-value" :class="card.highlight ? 'highlight' : ''">
          {{ card.value }}<span v-if="card.unit" class="metric-unit">{{ card.unit }}</span>
        </div>
        <div v-if="card.sub" class="metric-sub">{{ card.sub }}</div>
      </el-card>
    </div>

    <el-card shadow="never" class="chart-card">
      <div class="chart-title">OEE 与稼动趋势</div>
      <VChart v-if="trend.length" class="trend-chart" :option="chartOption" autoresize />
      <el-empty v-else description="暂无趋势数据" :image-size="80" />
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <span class="table-title">设备 OEE 明细</span>
          <el-tag size="small" type="info">共 {{ total }} 条</el-tag>
        </div>
        <div class="toolbar-right">
          <el-button :icon="Download" :loading="exporting" @click="handleExport">导出 Excel</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="period_date" label="日期" width="110" />
        <el-table-column prop="equipment_code" label="设备编号" width="120" />
        <el-table-column prop="equipment_name" label="设备名称" min-width="120" />
        <el-table-column prop="workshop" label="车间" min-width="110">
          <template #default="{ row }">{{ row.workshop || '—' }}</template>
        </el-table-column>
        <el-table-column prop="equipment_type" label="设备型号" min-width="100">
          <template #default="{ row }">{{ row.equipment_type || '—' }}</template>
        </el-table-column>
        <el-table-column prop="oee" label="OEE(%)" width="90" align="right">
          <template #default="{ row }">{{ formatPct(row.oee) }}</template>
        </el-table-column>
        <el-table-column prop="availability" label="时间稼动率(%)" width="120" align="right">
          <template #default="{ row }">{{ formatPct(row.availability) }}</template>
        </el-table-column>
        <el-table-column prop="performance" label="性能稼动率(%)" width="120" align="right">
          <template #default="{ row }">{{ formatPct(row.performance) }}</template>
        </el-table-column>
        <el-table-column prop="quality" label="良率(%)" width="90" align="right">
          <template #default="{ row }">{{ formatPct(row.quality) }}</template>
        </el-table-column>
        <el-table-column prop="utilization_rate" label="稼动率(%)" width="100" align="right">
          <template #default="{ row }">{{ formatPct(row.utilization_rate) }}</template>
        </el-table-column>
        <el-table-column prop="startup_rate" label="开机率(%)" width="100" align="right">
          <template #default="{ row }">{{ formatPct(row.startup_rate) }}</template>
        </el-table-column>
        <el-table-column prop="downtime_hours" label="停机时长(h)" width="110" align="right">
          <template #default="{ row }">{{ formatHours(row.downtime_hours) }}</template>
        </el-table-column>
        <el-table-column prop="output_qty" label="产量" width="80" align="right">
          <template #default="{ row }">{{ row.output_qty ?? '—' }}</template>
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
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import {
  exportEquipmentOeeReport,
  fetchEquipmentOeeFilters,
  fetchEquipmentOeeReport,
} from '../../api/reports/equipmentOee.js'

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
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const trend = ref([])
const summary = reactive({
  oee: 0,
  availability: 0,
  performance: 0,
  quality: 0,
  utilization_rate: 0,
  startup_rate: 0,
  downtime_hours: 0,
})
const dateRange = ref(defaultDateRange())
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
    list = list.filter((eq) => eq.workshop === filters.workshop)
  }
  if (filters.equipmentType) {
    list = list.filter((eq) => eq.equipment_type === filters.equipmentType)
  }
  return list
})

const metricCards = computed(() => [
  { key: 'oee', label: 'OEE 综合效率', value: formatPct(summary.oee), unit: '%', highlight: true, sub: '时间×性能×良率' },
  { key: 'availability', label: '时间稼动率', value: formatPct(summary.availability), unit: '%' },
  { key: 'performance', label: '性能稼动率', value: formatPct(summary.performance), unit: '%' },
  { key: 'quality', label: '良率', value: formatPct(summary.quality), unit: '%' },
  { key: 'utilization', label: '稼动率', value: formatPct(summary.utilization_rate), unit: '%' },
  { key: 'startup', label: '开机率', value: formatPct(summary.startup_rate), unit: '%' },
  { key: 'downtime', label: '停机时长', value: formatHours(summary.downtime_hours), unit: 'h' },
])

const chartOption = computed(() => {
  const dates = trend.value.map((p) => p.period_date)
  const seriesDefs = [
    { name: 'OEE', key: 'oee', color: '#409EFF' },
    { name: '时间稼动率', key: 'availability', color: '#67C23A' },
    { name: '性能稼动率', key: 'performance', color: '#E6A23C' },
    { name: '良率', key: 'quality', color: '#F56C6C' },
    { name: '稼动率', key: 'utilization_rate', color: '#909399' },
    { name: '开机率', key: 'startup_rate', color: '#626aef' },
  ]
  return {
    color: seriesDefs.map((s) => s.color),
    tooltip: { trigger: 'axis' },
    legend: { data: seriesDefs.map((s) => s.name), bottom: 0 },
    grid: { left: 48, right: 24, top: 24, bottom: 48 },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: { type: 'value', name: '%', min: 0, max: 100 },
    series: seriesDefs.map((s) => ({
      name: s.name,
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: trend.value.map((p) => p[s.key]),
    })),
  }
})

function formatPct(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
}

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
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
  summary.oee = s.oee ?? 0
  summary.availability = s.availability ?? 0
  summary.performance = s.performance ?? 0
  summary.quality = s.quality ?? 0
  summary.utilization_rate = s.utilization_rate ?? 0
  summary.startup_rate = s.startup_rate ?? 0
  summary.downtime_hours = s.downtime_hours ?? 0
}

async function loadFilters() {
  try {
    const resp = await fetchEquipmentOeeFilters()
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
    const resp = await fetchEquipmentOeeReport(buildQueryParams())
    items.value = resp.items || []
    total.value = resp.total || 0
    trend.value = resp.trend || []
    applySummary(resp)
  } catch (err) {
    items.value = []
    total.value = 0
    trend.value = []
    applySummary({})
    ElMessage.error(err?.message || '加载设备报表失败')
  } finally {
    loading.value = false
  }
}

function handleWorkshopChange() {
  if (!filters.equipmentId) return
  const selected = filterOptions.equipment.find((eq) => eq.id === filters.equipmentId)
  if (selected && filters.workshop && selected.workshop !== filters.workshop) {
    filters.equipmentId = null
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
    const blob = await exportEquipmentOeeReport(exportParams)
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `equipment_oee_${dateFrom.value || 'report'}.xlsx`
    link.click()
    URL.revokeObjectURL(link.href)
    ElMessage.success('导出成功')
  } catch (err) {
    ElMessage.error(err?.message || '导出失败')
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
.equipment-oee-page {
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
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
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
  font-size: 13px;
  font-weight: 400;
  margin-left: 2px;
}

.metric-sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
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
  flex-wrap: wrap;
  gap: 8px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
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
