<template>
  <div class="downtime-report-page">
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

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <span class="table-title">停机报表</span>
          <el-tag size="small" type="info">共 {{ total }} 条</el-tag>
          <el-tag size="small" type="warning">停机时长合计 {{ formatHours(downtimeHoursSum) }} h</el-tag>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="equipment_code" label="设备编号" width="120" />
        <el-table-column prop="equipment_name" label="设备名称" min-width="120" />
        <el-table-column prop="workshop" label="车间" min-width="110">
          <template #default="{ row }">{{ row.workshop || '—' }}</template>
        </el-table-column>
        <el-table-column label="开始时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.start_at) }}</template>
        </el-table-column>
        <el-table-column label="结束时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.end_at) }}</template>
        </el-table-column>
        <el-table-column prop="downtime_hours" label="停机时长(h)" width="120" align="right">
          <template #default="{ row }">{{ formatHours(row.downtime_hours) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center" />
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
import { ElMessage } from 'element-plus'
import {
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
const items = ref([])
const total = ref(0)
const downtimeHoursSum = ref(0)
const page = ref(1)
const pageSize = ref(10)
const dateRange = ref(defaultDateRange())
const filterOptions = reactive({
  workshops: [],
  equipment: [],
})

const filters = reactive({
  workshop: '',
  equipmentId: null,
})

const filteredEquipmentOptions = computed(() => {
  if (!filters.workshop) return filterOptions.equipment
  return filterOptions.equipment.filter((eq) => eq.workshop === filters.workshop)
})

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
}

function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}`
}

function handleWorkshopChange() {
  filters.equipmentId = null
}

async function loadFilters() {
  try {
    const resp = await fetchEquipmentDowntimeFilters()
    filterOptions.workshops = resp.workshops || []
    filterOptions.equipment = resp.equipment || []
  } catch {
    filterOptions.workshops = []
    filterOptions.equipment = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const resp = await fetchEquipmentDowntimeReport({
      page: page.value,
      pageSize: pageSize.value,
      dateFrom: (dateRange.value && dateRange.value[0]) || '',
      dateTo: (dateRange.value && dateRange.value[1]) || '',
      workshop: filters.workshop || undefined,
      equipmentId: filters.equipmentId || undefined,
    })
    items.value = resp.items || []
    total.value = resp.total || 0
    downtimeHoursSum.value = resp.downtime_hours_sum ?? 0
  } catch (err) {
    items.value = []
    total.value = 0
    downtimeHoursSum.value = 0
    ElMessage.error(err.message || '加载停机报表失败')
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
  filters.equipmentId = null
  dateRange.value = defaultDateRange()
  page.value = 1
  loadReport()
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
  gap: 12px;
}

.search-card,
.table-card {
  border-radius: 8px;
}

.search-form {
  margin-bottom: 0;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.table-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
