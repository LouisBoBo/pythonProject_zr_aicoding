<template>
  <div class="downtime-report-page">
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
        <el-form-item label="设备型号">
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
        <el-form-item label="停机类型">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 120px">
            <el-option
              v-for="s in filterOptions.downtimeStatuses"
              :key="s"
              :label="s"
              :value="s"
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
      </el-card>
    </div>

    <el-card shadow="never" class="chart-card">
      <div class="chart-title">停机趋势（次数 / 时长）</div>
      <VChart v-if="trend.length" class="trend-chart" :option="chartOption" autoresize />
      <el-empty v-else description="暂无趋势数据" :image-size="80" />
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-tabs v-model="activeTab" class="analysis-tabs">
        <el-tab-pane label="停机明细" name="detail">
          <div class="table-toolbar">
            <div class="toolbar-left">
              <span class="table-title">停机事件明细</span>
              <el-tag size="small" type="info">共 {{ total }} 条</el-tag>
            </div>
            <div class="toolbar-right">
              <el-button :icon="Download" :loading="exporting" @click="handleExport">导出 Excel</el-button>
            </div>
          </div>

          <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
            <el-table-column prop="equipment_code" label="设备编号" width="120" fixed="left" />
            <el-table-column prop="equipment_name" label="设备名称" min-width="120" />
            <el-table-column prop="workshop" label="车间" min-width="100">
              <template #default="{ row }">{{ row.workshop || '—' }}</template>
            </el-table-column>
            <el-table-column prop="equipment_type" label="设备型号" min-width="100">
              <template #default="{ row }">{{ row.equipment_type || '—' }}</template>
            </el-table-column>
            <el-table-column label="停机类型" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small" effect="light">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="开始时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.start_at) }}</template>
            </el-table-column>
            <el-table-column label="结束时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.end_at) }}</template>
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
        </el-tab-pane>

        <el-tab-pane label="按设备" name="by_equipment">
          <el-table :data="byEquipment" stripe border empty-text="暂无按设备统计">
            <el-table-column prop="dimension_label" label="名称" min-width="160" />
            <el-table-column prop="event_count" label="停机次数" width="100" align="right" />
            <el-table-column prop="downtime_hours" label="停机时长(h)" width="120" align="right" />
            <el-table-column prop="downtime_pct" label="时长占比(%)" width="120" align="right" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="按产线" name="by_line">
          <el-table :data="byLine" stripe border empty-text="暂无按产线统计">
            <el-table-column prop="dimension_label" label="名称" min-width="160" />
            <el-table-column prop="event_count" label="停机次数" width="100" align="right" />
            <el-table-column prop="downtime_hours" label="停机时长(h)" width="120" align="right" />
            <el-table-column prop="downtime_pct" label="时长占比(%)" width="120" align="right" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="按班次" name="by_shift">
          <el-table :data="byShift" stripe border empty-text="暂无按班次统计">
            <el-table-column prop="dimension_label" label="名称" min-width="160" />
            <el-table-column prop="event_count" label="停机次数" width="100" align="right" />
            <el-table-column prop="downtime_hours" label="停机时长(h)" width="120" align="right" />
            <el-table-column prop="downtime_pct" label="时长占比(%)" width="120" align="right" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="原因 Pareto" name="pareto">
          <el-table :data="reasonPareto" stripe border empty-text="暂无 Pareto 数据">
            <el-table-column prop="reason" label="停机类型/原因" min-width="140" />
            <el-table-column prop="event_count" label="次数" width="90" align="right" />
            <el-table-column prop="downtime_hours" label="时长(h)" width="100" align="right">
              <template #default="{ row }">{{ formatHours(row.downtime_hours) }}</template>
            </el-table-column>
            <el-table-column prop="cumulative_pct" label="累计占比(%)" width="120" align="right">
              <template #default="{ row }">{{ formatHours(row.cumulative_pct) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="MTBF / MTTR" name="reliability">
          <el-table :data="reliability" stripe border empty-text="暂无可靠性指标">
            <el-table-column prop="equipment_code" label="设备编号" width="120" />
            <el-table-column prop="equipment_name" label="设备名称" min-width="120" />
            <el-table-column prop="event_count" label="停机次数" width="100" align="right" />
            <el-table-column prop="mtbf_hours" label="MTBF(h)" width="110" align="right">
              <template #default="{ row }">{{ formatHours(row.mtbf_hours) }}</template>
            </el-table-column>
            <el-table-column prop="mttr_hours" label="MTTR(h)" width="110" align="right">
              <template #default="{ row }">{{ formatHours(row.mttr_hours) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
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
const activeTab = ref('detail')
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const trend = ref([])
const byEquipment = ref([])
const byLine = ref([])
const byShift = ref([])
const reasonPareto = ref([])
const reliability = ref([])
const summary = reactive({
  event_count: 0,
  total_downtime_hours: 0,
  avg_downtime_hours: 0,
  equipment_count: 0,
})
const dateRange = ref(defaultDateRange())
const filterOptions = reactive({
  workshops: [],
  equipmentTypes: [],
  equipment: [],
  downtimeStatuses: [],
})

const filters = reactive({
  workshop: '',
  equipmentType: '',
  equipmentId: null,
  status: '',
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
  {
    key: 'events',
    label: '停机事件数',
    value: summary.event_count,
    highlight: true,
  },
  {
    key: 'total',
    label: '停机总时长',
    value: formatHours(summary.total_downtime_hours),
    unit: 'h',
  },
  {
    key: 'avg',
    label: '平均单次时长',
    value: formatHours(summary.avg_downtime_hours),
    unit: 'h',
  },
  {
    key: 'equip',
    label: '涉及设备数',
    value: summary.equipment_count,
  },
])

const chartOption = computed(() => {
  const dates = trend.value.map((p) => p.period_date)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['停机次数', '停机时长(h)'], bottom: 0 },
    grid: { left: 48, right: 48, top: 24, bottom: 48 },
    xAxis: { type: 'category', data: dates, boundaryGap: true },
    yAxis: [
      { type: 'value', name: '次数', minInterval: 1 },
      { type: 'value', name: '小时' },
    ],
    series: [
      {
        name: '停机次数',
        type: 'bar',
        data: trend.value.map((p) => p.event_count),
        itemStyle: { color: '#409EFF' },
      },
      {
        name: '停机时长(h)',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        showSymbol: false,
        data: trend.value.map((p) => p.downtime_hours),
        itemStyle: { color: '#E6A23C' },
      },
    ],
  }
})

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
}

function formatDateTime(value) {
  if (!value) return '—'
  const s = String(value)
  if (s.includes('T')) {
    return s.replace('T', ' ').slice(0, 19)
  }
  return s
}

function statusTagType(status) {
  if (status === '停机') return 'danger'
  if (status === '维修') return 'warning'
  if (status === '待机') return 'info'
  return ''
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
    status: filters.status || undefined,
  }
}

function applyReportPayload(data) {
  const s = data?.summary || {}
  summary.event_count = s.event_count ?? 0
  summary.total_downtime_hours = s.total_downtime_hours ?? 0
  summary.avg_downtime_hours = s.avg_downtime_hours ?? 0
  summary.equipment_count = s.equipment_count ?? 0
  trend.value = data?.trend || []
  byEquipment.value = data?.by_equipment || []
  byLine.value = data?.by_line || []
  byShift.value = data?.by_shift || []
  reasonPareto.value = data?.reason_pareto || []
  reliability.value = data?.reliability || []
}

async function loadFilters() {
  try {
    const resp = await fetchEquipmentDowntimeFilters()
    filterOptions.workshops = resp.workshops || []
    filterOptions.equipmentTypes = resp.equipment_types || []
    filterOptions.equipment = resp.equipment || []
    filterOptions.downtimeStatuses = resp.downtime_statuses || []
  } catch {
    filterOptions.workshops = []
    filterOptions.equipmentTypes = []
    filterOptions.equipment = []
    filterOptions.downtimeStatuses = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const resp = await fetchEquipmentDowntimeReport(buildQueryParams())
    items.value = resp.items || []
    total.value = resp.total || 0
    applyReportPayload(resp)
  } catch (err) {
    items.value = []
    total.value = 0
    applyReportPayload({})
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
  filters.equipmentType = ''
  filters.equipmentId = null
  filters.status = ''
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
    link.download = `downtime_report_${dateFrom.value || 'export'}.xlsx`
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

.analysis-tabs :deep(.el-tabs__content) {
  padding-top: 4px;
}
</style>
