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
          <el-button :loading="exporting" @click="handleExport">导出 Excel</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div class="summary-row">
      <el-card shadow="never" class="summary-card">
        <div class="summary-label">停机次数</div>
        <div class="summary-value">{{ summary.event_count }}</div>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <div class="summary-label">停机时长合计</div>
        <div class="summary-value">{{ formatHours(summary.total_duration_hours) }}<span class="unit">h</span></div>
      </el-card>
    </div>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <span class="table-title">设备停机报表</span>
          <el-tag size="small" type="info">运行日志 · 停机时段</el-tag>
        </div>
        <div class="toolbar-right">
          <span class="sum-text">共 {{ total }} 条</span>
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
import { ElMessage } from 'element-plus'
import {
  exportEquipmentDowntimeReport,
  fetchEquipmentDowntimeFilters,
  fetchEquipmentDowntimeReport,
} from '../../api/reports/equipmentDowntime.js'

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
const summary = reactive({
  event_count: 0,
  total_duration_hours: 0,
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
    summary.event_count = data.summary?.event_count ?? 0
    summary.total_duration_hours = data.summary?.total_duration_hours ?? 0
  } catch (err) {
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

.search-form {
  flex-wrap: wrap;
}

.summary-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.summary-card {
  flex: 1;
  min-width: 160px;
}

.summary-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.summary-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.summary-value .unit {
  font-size: 14px;
  font-weight: normal;
  margin-left: 4px;
  color: var(--el-text-color-secondary);
}

.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.table-title {
  font-weight: 600;
  font-size: 15px;
}

.sum-text {
  font-size: 13px;
  color: var(--el-text-color-secondary);
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
