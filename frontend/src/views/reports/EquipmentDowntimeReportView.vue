<template>
  <div class="equipment-downtime-page">
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
            @change="handleWorkshopChange"
          >
            <el-option v-for="w in filterOptions.workshops" :key="w" :label="w" :value="w" />
          </el-select>
        </el-form-item>
        <el-form-item label="设备">
          <el-select
            v-model="filters.equipmentId"
            placeholder="全部"
            clearable
            filterable
            style="width: 220px"
          >
            <el-option
              v-for="eq in filteredEquipmentOptions"
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
            filterable
            style="width: 150px"
          >
            <el-option
              v-for="reason in filterOptions.downtimeReasons"
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

    <div class="charts-row">
      <el-card shadow="never" class="chart-card">
        <div class="chart-title">按日停机趋势</div>
        <VChart v-if="trend.length" class="trend-chart" :option="trendChartOption" autoresize />
        <el-empty v-else description="暂无趋势数据" :image-size="80" />
      </el-card>
      <el-card shadow="never" class="chart-card">
        <div class="chart-title">设备停机对比（Top 10）</div>
        <VChart v-if="topEquipment.length" class="trend-chart" :option="barChartOption" autoresize />
        <el-empty v-else description="暂无对比数据" :image-size="80" />
      </el-card>
    </div>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <span class="table-title">按设备汇总</span>
          <el-tag size="small" type="info">共 {{ total }} 台设备</el-tag>
        </div>
        <div class="toolbar-right">
          <el-button :icon="Download" :loading="exporting" @click="handleExport">导出 Excel</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="equipment_code" label="设备编码" width="120" />
        <el-table-column prop="equipment_name" label="设备名称" min-width="130" />
        <el-table-column prop="workshop" label="车间/产线" min-width="110">
          <template #default="{ row }">{{ row.workshop || '—' }}</template>
        </el-table-column>
        <el-table-column prop="event_count" label="停机次数" width="100" align="right" />
        <el-table-column prop="duration_hours" label="停机时长(h)" width="120" align="right">
          <template #default="{ row }">{{ formatHours(row.duration_hours) }}</template>
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
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import {
  exportEquipmentDowntimeReport,
  fetchEquipmentDowntimeFilters,
  fetchEquipmentDowntimeReport,
} from '../../api/reports/equipmentDowntime.js'

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent])

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
const topEquipment = ref([])
const summary = reactive({
  event_count: 0,
  total_duration_hours: 0,
  avg_duration_hours: 0,
  equipment_count: 0,
})
const dateRange = ref(defaultDateRange())
const filterOptions = reactive({
  workshops: [],
  downtimeReasons: [],
  equipment: [],
})

const filters = reactive({
  workshop: '',
  equipmentId: null,
  downtimeReason: '',
})

const dateFrom = computed(() => (dateRange.value && dateRange.value[0]) || '')
const dateTo = computed(() => (dateRange.value && dateRange.value[1]) || '')

const filteredEquipmentOptions = computed(() => {
  let list = filterOptions.equipment || []
  if (filters.workshop) {
    list = list.filter((eq) => eq.workshop === filters.workshop)
  }
  return list
})

const metricCards = computed(() => [
  {
    key: 'events',
    label: '停机次数',
    value: summary.event_count,
    highlight: true,
  },
  {
    key: 'duration',
    label: '停机时长合计',
    value: formatHours(summary.total_duration_hours),
    unit: 'h',
  },
  {
    key: 'avg',
    label: '单次平均停机',
    value: formatHours(summary.avg_duration_hours),
    unit: 'h',
  },
  {
    key: 'equipment',
    label: '涉及设备',
    value: summary.equipment_count,
    unit: '台',
  },
])

const trendChartOption = computed(() => {
  const dates = trend.value.map((p) => p.period_date)
  return {
    color: ['#409EFF', '#E6A23C'],
    tooltip: { trigger: 'axis' },
    legend: { data: ['停机时长(h)', '停机次数'], bottom: 0 },
    grid: { left: 48, right: 48, top: 24, bottom: 48 },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: [
      { type: 'value', name: '时长(h)', min: 0 },
      { type: 'value', name: '次数', min: 0, splitLine: { show: false } },
    ],
    series: [
      {
        name: '停机时长(h)',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: trend.value.map((p) => p.duration_hours),
      },
      {
        name: '停机次数',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        showSymbol: false,
        data: trend.value.map((p) => p.event_count),
      },
    ],
  }
})

const barChartOption = computed(() => {
  const labels = topEquipment.value.map(
    (eq) => (eq.equipment_name?.length > 8 ? `${eq.equipment_name.slice(0, 8)}…` : eq.equipment_name) || eq.equipment_code,
  )
  return {
    color: ['#409EFF', '#67C23A'],
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['停机时长(h)', '停机次数'], bottom: 0 },
    grid: { left: 48, right: 24, top: 24, bottom: 64 },
    xAxis: { type: 'category', data: labels, axisLabel: { interval: 0, rotate: labels.length > 6 ? 30 : 0 } },
    yAxis: { type: 'value', name: '时长(h)', min: 0 },
    series: [
      {
        name: '停机时长(h)',
        type: 'bar',
        data: topEquipment.value.map((eq) => eq.duration_hours),
      },
      {
        name: '停机次数',
        type: 'bar',
        data: topEquipment.value.map((eq) => eq.event_count),
      },
    ],
  }
})

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
    equipmentId: filters.equipmentId || undefined,
    downtimeReason: filters.downtimeReason || undefined,
  }
}

function applySummary(data) {
  const s = data?.summary || {}
  summary.event_count = s.event_count ?? 0
  summary.total_duration_hours = s.total_duration_hours ?? 0
  summary.avg_duration_hours = s.avg_duration_hours ?? 0
  summary.equipment_count = s.equipment_count ?? 0
}

async function loadFilters() {
  try {
    const resp = await fetchEquipmentDowntimeFilters()
    filterOptions.workshops = resp.workshops || []
    filterOptions.downtimeReasons = resp.downtime_reasons || []
    filterOptions.equipment = resp.equipment || []
  } catch {
    filterOptions.workshops = []
    filterOptions.downtimeReasons = []
    filterOptions.equipment = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const resp = await fetchEquipmentDowntimeReport(buildQueryParams())
    items.value = resp.items || []
    total.value = resp.total || 0
    trend.value = resp.trend || []
    topEquipment.value = resp.top_equipment || []
    applySummary(resp)
  } catch (err) {
    items.value = []
    total.value = 0
    trend.value = []
    topEquipment.value = []
    applySummary({})
    ElMessage.error(err?.message || '加载停机报表失败')
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
  filters.equipmentId = null
  filters.downtimeReason = ''
  page.value = 1
  loadReport()
}

async function handleExport() {
  exporting.value = true
  try {
    const { page: _p, pageSize: _s, ...exportParams } = buildQueryParams()
    const blob = await exportEquipmentDowntimeReport(exportParams)
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `equipment_downtime_${dateFrom.value || 'report'}.xlsx`
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
.equipment-downtime-page {
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
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
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

.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 16px;
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