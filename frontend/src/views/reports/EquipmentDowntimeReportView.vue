<template>
  <div class="downtime-report-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="日期模式">
          <el-radio-group v-model="dateMode" @change="handleDateModeChange">
            <el-radio-button value="single">单日</el-radio-button>
            <el-radio-button value="range">区间</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="停机日期">
          <el-date-picker
            v-if="dateMode === 'single'"
            v-model="singleDate"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            clearable
            style="width: 160px"
          />
          <el-date-picker
            v-else
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
        <el-form-item label="产线">
          <el-select
            v-model="filters.productionLine"
            placeholder="全部"
            clearable
            style="width: 140px"
          >
            <el-option
              v-for="line in productionLineOptions"
              :key="line"
              :label="line"
              :value="line"
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
        <el-form-item label="车间">
          <el-select
            v-model="filters.workshop"
            placeholder="全部"
            clearable
            style="width: 140px"
          >
            <el-option
              v-for="ws in workshopOptions"
              :key="ws"
              :label="ws"
              :value="ws"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="停机原因">
          <el-select
            v-model="filters.downtimeReason"
            placeholder="全部"
            clearable
            style="width: 130px"
          >
            <el-option
              v-for="reason in downtimeReasonOptions"
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

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <span class="table-title">停机报表</span>
          <el-tag size="small" type="info">按设备停机时段（equipment_runtime_logs）</el-tag>
        </div>
        <div class="toolbar-right">
          <span class="sum-text">停机次数 {{ summary.event_count }}</span>
          <span class="sum-text">停机时长合计 {{ formatHours(summary.total_duration_hours) }} h</span>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%" empty-text="暂无停机记录">
        <el-table-column label="设备" min-width="160" fixed="left">
          <template #default="{ row }">
            <div class="cell-device">
              <span class="device-name">{{ row.equipment_name || '—' }}</span>
              <span class="device-code">{{ row.equipment_code || '—' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="production_line" label="产线" min-width="110">
          <template #default="{ row }">{{ row.production_line || '—' }}</template>
        </el-table-column>
        <el-table-column prop="workshop" label="车间" min-width="100">
          <template #default="{ row }">{{ row.workshop || '—' }}</template>
        </el-table-column>
        <el-table-column label="停机开始" width="160">
          <template #default="{ row }">{{ formatDateTime(row.start_at) }}</template>
        </el-table-column>
        <el-table-column label="停机结束" width="160">
          <template #default="{ row }">{{ formatDateTime(row.end_at) }}</template>
        </el-table-column>
        <el-table-column label="停机时长(h)" width="110" align="right">
          <template #default="{ row }">{{ formatHours(row.duration_hours) }}</template>
        </el-table-column>
        <el-table-column prop="downtime_reason" label="停机原因" min-width="100">
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
import { ElMessage } from 'element-plus'
import {
  fetchEquipmentDowntimeFilters,
  fetchEquipmentDowntimeReport,
} from '../../api/reports/equipmentDowntime.js'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const dateMode = ref('range')
const singleDate = ref('')
const dateRange = ref([])

const workshopOptions = ref([])
const productionLineOptions = ref([])
const downtimeReasonOptions = ref([])
const equipmentOptions = ref([])

const summary = reactive({
  event_count: 0,
  total_duration_hours: 0,
})

const filters = reactive({
  workshop: '',
  productionLine: '',
  equipmentId: null,
  downtimeReason: '',
})

const filteredEquipmentOptions = computed(() => {
  if (!filters.workshop) return equipmentOptions.value
  return equipmentOptions.value.filter((eq) => eq.workshop === filters.workshop)
})

watch(
  () => filters.workshop,
  () => {
    if (!filters.equipmentId) return
    const selected = equipmentOptions.value.find((eq) => eq.id === filters.equipmentId)
    if (selected && filters.workshop && selected.workshop !== filters.workshop) {
      filters.equipmentId = null
    }
  }
)

watch(
  () => filters.productionLine,
  () => {
    if (!filters.equipmentId) return
    const selected = equipmentOptions.value.find((eq) => eq.id === filters.equipmentId)
    if (
      selected &&
      filters.productionLine &&
      !(selected.production_line || '').includes(filters.productionLine)
    ) {
      filters.equipmentId = null
    }
  }
)

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
  dateRange.value = [fmt(start), fmt(end)]
}

function handleDateModeChange() {
  if (dateMode.value === 'range' && !dateRange.value?.length) {
    defaultDateRange()
  }
}

function resolveDateRange() {
  if (dateMode.value === 'single' && singleDate.value) {
    return { dateFrom: singleDate.value, dateTo: singleDate.value }
  }
  if (dateMode.value === 'range' && dateRange.value?.length === 2) {
    return { dateFrom: dateRange.value[0], dateTo: dateRange.value[1] }
  }
  return { dateFrom: undefined, dateTo: undefined }
}

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '0'
  return n % 1 === 0 ? String(n) : n.toFixed(2)
}

function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${y}-${m}-${day} ${hh}:${mm}:${ss}`
}

async function loadFilters() {
  try {
    const resp = await fetchEquipmentDowntimeFilters()
    workshopOptions.value = resp.workshops || []
    productionLineOptions.value = resp.production_lines || []
    downtimeReasonOptions.value = resp.downtime_reasons || []
    equipmentOptions.value = resp.equipment || []
  } catch {
    workshopOptions.value = []
    productionLineOptions.value = []
    downtimeReasonOptions.value = []
    equipmentOptions.value = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const { dateFrom, dateTo } = resolveDateRange()
    const resp = await fetchEquipmentDowntimeReport({
      page: page.value,
      pageSize: pageSize.value,
      dateFrom,
      dateTo,
      workshop: filters.workshop || undefined,
      productionLine: filters.productionLine || undefined,
      equipmentId: filters.equipmentId || undefined,
      downtimeReason: filters.downtimeReason || undefined,
    })
    items.value = resp.items || []
    total.value = resp.total || 0
    summary.event_count = resp.summary?.event_count ?? 0
    summary.total_duration_hours = resp.summary?.total_duration_hours ?? 0
  } catch (err) {
    ElMessage.error(err.message || '加载停机报表失败')
    items.value = []
    total.value = 0
    summary.event_count = 0
    summary.total_duration_hours = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadReport()
}

function handleReset() {
  filters.workshop = ''
  filters.productionLine = ''
  filters.equipmentId = null
  filters.downtimeReason = ''
  dateMode.value = 'range'
  defaultDateRange()
  page.value = 1
  loadReport()
}

onMounted(async () => {
  defaultDateRange()
  await loadFilters()
  await loadReport()
})
</script>

<style scoped>
.downtime-report-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.search-card :deep(.el-card__body) {
  padding-bottom: 4px;
}

.table-card :deep(.el-card__body) {
  padding-top: 12px;
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
  gap: 8px;
  flex-wrap: wrap;
}

.table-title {
  font-weight: 600;
  font-size: 15px;
}

.sum-text {
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.cell-device {
  display: flex;
  flex-direction: column;
  gap: 2px;
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