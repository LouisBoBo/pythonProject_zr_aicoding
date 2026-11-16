<template>
  <div class="work-hours-page">
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
        <el-form-item label="部门">
          <el-select
            v-model="filters.department"
            placeholder="全部"
            clearable
            filterable
            style="width: 160px"
          >
            <el-option v-for="dept in departmentOptions" :key="dept" :label="dept" :value="dept" />
          </el-select>
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
              :label="`${emp.employee_name}（${emp.employee_no}）`"
              :value="emp.employee_no"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="视图">
          <el-radio-group v-model="viewMode" @change="handleViewModeChange">
            <el-radio-button value="employee_date">按人按日</el-radio-button>
            <el-radio-button value="employee">按员工汇总</el-radio-button>
          </el-radio-group>
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
          <el-tag size="small" type="info">
            {{ viewMode === 'employee' ? '按员工汇总' : '按人按日明细' }}
          </el-tag>
        </div>
        <div class="toolbar-right">
          <span class="sum-text">报工合计 {{ formatHours(totals.workHoursSum) }} h</span>
          <span class="sum-text">加班合计 {{ formatHours(totals.overtimeHoursSum) }} h</span>
          <span class="sum-text">总计 {{ formatHours(totals.totalWorkHoursSum) }} h</span>
          <span class="sum-text">员工 {{ totals.employeeCount }} 人</span>
          <el-button :icon="Download" :loading="exporting" @click="handleExport">导出 Excel</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="employee_name" label="员工" min-width="110" fixed="left" />
        <el-table-column prop="employee_no" label="工号" width="110" />
        <el-table-column prop="department" label="部门" min-width="120" />
        <el-table-column
          v-if="viewMode === 'employee_date'"
          prop="work_date"
          label="日期"
          width="120"
          sortable="custom"
        >
          <template #default="{ row }">{{ row.work_date || '—' }}</template>
        </el-table-column>
        <el-table-column
          v-if="viewMode === 'employee_date'"
          prop="shift_type_label"
          label="班别"
          width="90"
        >
          <template #default="{ row }">{{ row.shift_type_label || '—' }}</template>
        </el-table-column>
        <el-table-column prop="work_hours" label="报工工时(h)" width="120" align="right">
          <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
        </el-table-column>
        <el-table-column prop="overtime_hours" label="加班(h)" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.overtime_hours) }}</template>
        </el-table-column>
        <el-table-column prop="total_work_hours" label="合计(h)" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.total_work_hours) }}</template>
        </el-table-column>
        <el-table-column
          v-if="viewMode === 'employee_date'"
          prop="work_order_count"
          label="工单数"
          width="90"
          align="right"
        >
          <template #default="{ row }">{{ row.work_order_count ?? '—' }}</template>
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
  exportEmployeeWorkHoursReport,
  fetchEmployeeWorkHourFilters,
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
const departmentOptions = ref([])
const employeeOptions = ref([])
const dateRange = ref(defaultDateRange())
const viewMode = ref('employee_date')

const filters = reactive({
  department: '',
  employeeNo: '',
})

const totals = reactive({
  workHoursSum: 0,
  overtimeHoursSum: 0,
  totalWorkHoursSum: 0,
  employeeCount: 0,
})

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
}

function buildListParams() {
  return {
    page: page.value,
    pageSize: pageSize.value,
    dateFrom: dateRange.value?.[0] || undefined,
    dateTo: dateRange.value?.[1] || undefined,
    department: filters.department || undefined,
    employeeNo: filters.employeeNo || undefined,
    dimension: viewMode.value,
  }
}

function buildExportParams() {
  const { page: _p, pageSize: _s, dimension: _d, ...rest } = buildListParams()
  return rest
}

function handleViewModeChange() {
  page.value = 1
  loadReport()
}

async function loadFilters() {
  try {
    const resp = await fetchEmployeeWorkHourFilters()
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
    const resp = await fetchEmployeeWorkHoursReport(buildListParams())
    items.value = resp.items || []
    total.value = resp.total || 0
    totals.workHoursSum = resp.work_hours_sum ?? 0
    totals.overtimeHoursSum = resp.overtime_hours_sum ?? 0
    totals.totalWorkHoursSum = resp.total_work_hours_sum ?? 0
    totals.employeeCount = resp.employee_count ?? 0
  } catch (err) {
    items.value = []
    total.value = 0
    totals.workHoursSum = 0
    totals.overtimeHoursSum = 0
    totals.totalWorkHoursSum = 0
    totals.employeeCount = 0
    ElMessage.error(err.message || '加载员工工时报表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadReport()
}

function handleReset() {
  filters.department = ''
  filters.employeeNo = ''
  dateRange.value = defaultDateRange()
  viewMode.value = 'employee_date'
  page.value = 1
  loadReport()
}

async function handleExport() {
  exporting.value = true
  try {
    const blob = await exportEmployeeWorkHoursReport(buildExportParams())
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `employee_work_hours_${new Date().toISOString().slice(0, 10)}.xlsx`
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
.work-hours-page {
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
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.table-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.sum-text {
  white-space: nowrap;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
