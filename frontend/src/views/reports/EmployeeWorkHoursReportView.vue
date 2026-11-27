<template>
  <div class="employee-work-hours-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="日期区间">
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
        <el-form-item label="员工">
          <el-select
            v-model="filters.employeeNo"
            placeholder="全部"
            clearable
            filterable
            style="width: 200px"
          >
            <el-option
              v-for="emp in employeeOptions"
              :key="emp.employee_no"
              :label="emp.label"
              :value="emp.employee_no"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-select
            v-model="filters.department"
            placeholder="全部"
            clearable
            style="width: 140px"
          >
            <el-option v-for="dep in departmentOptions" :key="dep" :label="dep" :value="dep" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键字">
          <el-input
            v-model="filters.keyword"
            placeholder="工号 / 姓名"
            clearable
            style="width: 140px"
            @keyup.enter="handleSearch"
          />
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
          <el-tag size="small" type="info">员工 × 日期 · 演示数据</el-tag>
        </div>
        <div class="toolbar-right">
          <span class="sum-text">出勤合计 {{ formatHours(summary.attendance_hours_sum) }}</span>
          <span class="sum-text">加班合计 {{ formatHours(summary.overtime_hours_sum) }}</span>
          <span class="sum-text">工时合计 {{ formatHours(summary.total_hours_sum) }}</span>
          <el-button :icon="Download" :loading="exporting" @click="handleExport">导出</el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="items"
        stripe
        border
        show-summary
        :summary-method="summaryMethod"
        style="width: 100%"
        empty-text="暂无工时明细"
      >
        <el-table-column prop="work_date" label="日期" width="120" />
        <el-table-column prop="employee_no" label="工号" width="100" />
        <el-table-column prop="employee_name" label="姓名" width="100" />
        <el-table-column prop="department" label="部门" min-width="110" />
        <el-table-column prop="attendance_hours" label="出勤工时" width="110" align="right">
          <template #default="{ row }">{{ formatHours(row.attendance_hours) }}</template>
        </el-table-column>
        <el-table-column prop="overtime_hours" label="加班工时" width="110" align="right">
          <template #default="{ row }">{{ formatHours(row.overtime_hours) }}</template>
        </el-table-column>
        <el-table-column prop="total_hours" label="合计" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.total_hours) }}</template>
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
import { onMounted, reactive, ref } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  exportEmployeeWorkHoursDemoCsv,
  fetchEmployeeWorkHoursFilters,
  fetchEmployeeWorkHoursReport,
} from '../../api/reports/employeeWorkHours.js'

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
const employeeOptions = ref([])
const departmentOptions = ref([])

const filters = reactive({
  employeeNo: '',
  department: '',
  keyword: '',
})

const summary = reactive({
  attendance_hours_sum: 0,
  overtime_hours_sum: 0,
  total_hours_sum: 0,
})

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(1)
}

function buildQueryParams() {
  return {
    page: page.value,
    pageSize: pageSize.value,
    dateFrom: dateRange.value?.[0] || undefined,
    dateTo: dateRange.value?.[1] || undefined,
    employeeNo: filters.employeeNo || undefined,
    department: filters.department || undefined,
    keyword: filters.keyword.trim() || undefined,
  }
}

function summaryMethod({ columns }) {
  const sums = []
  columns.forEach((column, index) => {
    if (index === 0) {
      sums[index] = '合计'
      return
    }
    const prop = column.property
    if (prop === 'attendance_hours') {
      sums[index] = formatHours(summary.attendance_hours_sum)
    } else if (prop === 'overtime_hours') {
      sums[index] = formatHours(summary.overtime_hours_sum)
    } else if (prop === 'total_hours') {
      sums[index] = formatHours(summary.total_hours_sum)
    } else {
      sums[index] = ''
    }
  })
  return sums
}

async function loadFilters() {
  try {
    const resp = await fetchEmployeeWorkHoursFilters()
    employeeOptions.value = resp.employees || []
    departmentOptions.value = resp.departments || []
  } catch {
    employeeOptions.value = []
    departmentOptions.value = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const resp = await fetchEmployeeWorkHoursReport(buildQueryParams())
    items.value = resp.items || []
    total.value = resp.total || 0
    summary.attendance_hours_sum = resp.attendance_hours_sum || 0
    summary.overtime_hours_sum = resp.overtime_hours_sum || 0
    summary.total_hours_sum = resp.total_hours_sum || 0
  } catch (err) {
    ElMessage.error(err.message || '加载员工工时报表失败')
    items.value = []
    total.value = 0
    summary.attendance_hours_sum = 0
    summary.overtime_hours_sum = 0
    summary.total_hours_sum = 0
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
  filters.employeeNo = ''
  filters.department = ''
  filters.keyword = ''
  page.value = 1
  loadReport()
}

async function handleExport() {
  exporting.value = true
  try {
    const { page: _p, pageSize: _s, ...exportParams } = buildQueryParams()
    const { blob, rowCount } = await exportEmployeeWorkHoursDemoCsv(exportParams)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `employee_work_hours_${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success(`已导出 ${rowCount} 条明细（演示 CSV，接口就绪后对接后端）`)
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
.employee-work-hours-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.search-card,
.table-card {
  border-radius: 4px;
}

.search-form {
  margin-bottom: -8px;
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

.sum-text {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>