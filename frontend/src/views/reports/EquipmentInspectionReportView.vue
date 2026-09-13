<template>
  <div class="inspection-report-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="点检日期">
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
            v-model="filters.deviceId"
            placeholder="全部"
            clearable
            filterable
            style="width: 200px"
          >
            <el-option
              v-for="dev in deviceOptions"
              :key="dev.id"
              :label="`${dev.name}（${dev.code}）`"
              :value="dev.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="点检状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="正常" value="normal" />
            <el-option label="异常" value="abnormal" />
            <el-option label="草稿" value="draft" />
            <el-option label="未完成" value="incomplete" />
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
          <span class="table-title">设备点检报表</span>
          <el-tag size="small" type="info">点检明细</el-tag>
        </div>
        <div class="toolbar-right">
          <span class="sum-text">共 {{ total }} 条</span>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="inspect_date" label="点检日期" width="120" />
        <el-table-column label="设备" min-width="160">
          <template #default="{ row }">
            <div class="cell-device">
              <span class="device-name">{{ row.device_name }}</span>
              <span class="device-code">{{ row.device_code }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="workshop" label="车间" width="100">
          <template #default="{ row }">{{ row.workshop || '—' }}</template>
        </el-table-column>
        <el-table-column prop="item_name" label="点检项" min-width="120" />
        <el-table-column prop="standard_value" label="标准值" width="110">
          <template #default="{ row }">{{ row.standard_value || '—' }}</template>
        </el-table-column>
        <el-table-column prop="actual_value" label="实测值" width="110">
          <template #default="{ row }">{{ row.actual_value || '—' }}</template>
        </el-table-column>
        <el-table-column label="点检结果" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="resultTagType(row.result)" size="small" effect="light">
              {{ resultLabel(row.result) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="记录状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.record_status)" size="small" effect="light">
              {{ statusLabel(row.record_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="inspector" label="点检人" width="90" />
        <el-table-column prop="item_remark" label="备注" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.item_remark || '—' }}</template>
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
  fetchEquipmentInspectionFilters,
  fetchEquipmentInspectionReport,
} from '../../api/reports/equipmentInspection.js'

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
const page = ref(1)
const pageSize = ref(10)
const dateRange = ref(defaultDateRange())
const filterOptions = reactive({
  workshops: [],
  devices: [],
})

const filters = reactive({
  workshop: '',
  deviceId: null,
  status: '',
})

const deviceOptions = computed(() => {
  if (!filters.workshop) return filterOptions.devices
  return filterOptions.devices.filter((dev) => dev.workshop === filters.workshop)
})

watch(
  () => filters.workshop,
  () => {
    if (!filters.deviceId) return
    const selected = filterOptions.devices.find((dev) => dev.id === filters.deviceId)
    if (selected && filters.workshop && selected.workshop !== filters.workshop) {
      filters.deviceId = null
    }
  },
)

function resultLabel(result) {
  if (result === 'OK') return '合格'
  if (result === 'NG') return '不合格'
  return result || '—'
}

function resultTagType(result) {
  if (result === 'OK') return 'success'
  if (result === 'NG') return 'danger'
  return 'info'
}

function statusLabel(status) {
  const map = {
    normal: '正常',
    abnormal: '异常',
    draft: '草稿',
    incomplete: '未完成',
  }
  return map[status] || status || '—'
}

function statusTagType(status) {
  const map = {
    normal: 'success',
    abnormal: 'danger',
    draft: 'info',
    incomplete: 'warning',
  }
  return map[status] || 'info'
}

async function loadFilters() {
  try {
    const data = await fetchEquipmentInspectionFilters()
    filterOptions.workshops = data.workshops || []
    filterOptions.devices = data.devices || []
  } catch (err) {
    ElMessage.error(err.message || '加载筛选选项失败')
  }
}

async function loadReport() {
  loading.value = true
  try {
    const [dateFrom, dateTo] = dateRange.value || []
    const data = await fetchEquipmentInspectionReport({
      page: page.value,
      pageSize: pageSize.value,
      dateFrom,
      dateTo,
      deviceId: filters.deviceId || undefined,
      workshop: filters.workshop || undefined,
      status: filters.status || undefined,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    ElMessage.error(err.message || '加载报表失败')
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
  filters.deviceId = null
  filters.status = ''
  page.value = 1
  loadReport()
}

onMounted(async () => {
  await loadFilters()
  await loadReport()
})
</script>

<style scoped>
.inspection-report-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-card,
.table-card {
  border-radius: 8px;
}

.search-form {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 0;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.table-title {
  font-size: 16px;
  font-weight: 600;
}

.sum-text {
  color: var(--el-text-color-secondary);
  font-size: 13px;
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
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
