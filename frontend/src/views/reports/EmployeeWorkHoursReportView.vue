<template>
  <div class="employee-work-hours-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="日期模式">
          <el-radio-group v-model="dateMode" @change="handleDateModeChange">
            <el-radio-button value="single">单日</el-radio-button>
            <el-radio-button value="range">区间</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="报工日期">
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
        <el-form-item label="员工">
          <el-select
            v-model="filters.employeeNo"
            placeholder="全部"
            clearable
            filterable
            style="width: 160px"
          >
            <el-option
              v-for="emp in employeeOptions"
              :key="emp.employee_no"
              :label="`${emp.employee_name}（${emp.employee_no}）`"
              :value="emp.employee_no"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="部门/班组">
          <el-select
            v-model="filters.departmentName"
            placeholder="全部"
            clearable
            style="width: 140px"
          >
            <el-option
              v-for="dept in departmentOptions"
              :key="dept"
              :label="dept"
              :value="dept"
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
          <span class="table-title">员工工时报表</span>
          <el-tag size="small" type="info">工单报工明细（员工 × 日期 × 工单）</el-tag>
        </div>
        <div class="toolbar-right">
          <span class="sum-text">工时合计 {{ formatHours(workHoursSum) }}</span>
        </div>
      </div>

      <el-table v-loading="loading" :data="tableRows" stripe border style="width: 100%">
        <el-table-column prop="employee_name" label="员工" min-width="100" />
        <el-table-column prop="department_name" label="部门/班组" min-width="110" />
        <el-table-column prop="work_date" label="日期" width="120" />
        <el-table-column prop="order_no" label="工单号" min-width="130" />
        <el-table-column prop="process" label="工序" min-width="100" />
        <el-table-column prop="work_hours" label="工时（小时）" width="120" align="right">
          <template #default="{ row }">
            <template v-if="!row._isTotal">{{ formatHours(row.work_hours) }}</template>
            <strong v-else>{{ formatHours(row.work_hours) }}</strong>
          </template>
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
import { ElMessage } from 'element-plus'
import {
  fetchEmployeeWorkHoursFilters,
  fetchEmployeeWorkHoursReport,
} from '../../api/reports/employeeWorkHours.js'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const workHoursSum = ref(0)
const page = ref(1)
const pageSize = ref(10)
const dateMode = ref('range')
const singleDate = ref('')
const dateRange = ref([])
const employeeOptions = ref([])
const departmentOptions = ref([])

const filters = reactive({
  employeeNo: '',
  departmentName: '',
})

const tableRows = computed(() => {
  const rows = items.value || []
  if (!rows.length) return rows
  return [
    ...rows,
    {
      _isTotal: true,
      employee_name: '合计',
      department_name: '—',
      work_date: '—',
      order_no: '—',
      process: '—',
      work_hours: workHoursSum.value,
    },
  ]
})

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '0'
  return n % 1 === 0 ? String(n) : n.toFixed(2)
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

async function loadFilters() {
  try {
    const resp = await fetchEmployeeWorkHoursFilters()
    departmentOptions.value = resp.departments || []
    employeeOptions.value = resp.employees || []
  } catch {
    departmentOptions.value = []
    employeeOptions.value = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const { dateFrom, dateTo } = resolveDateRange()
    const resp = await fetchEmployeeWorkHoursReport({
      page: page.value,
      pageSize: pageSize.value,
      dateFrom,
      dateTo,
      employeeNo: filters.employeeNo || undefined,
      departmentName: filters.departmentName || undefined,
    })
    items.value = resp.items || []
    total.value = resp.total || 0
    workHoursSum.value = resp.work_hours_sum ?? 0
  } catch (err) {
    ElMessage.error(err.message || '加载报表失败')
    items.value = []
    total.value = 0
    workHoursSum.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadReport()
}

function handleReset() {
  filters.employeeNo = ''
  filters.departmentName = ''
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
.employee-work-hours-page {
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
  color: var(--el-text-color-regular);
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
