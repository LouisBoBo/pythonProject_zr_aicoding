<template>
  <div class="work-hours-page">
    <el-card shadow="never" class="search-card">
      <div class="page-heading">
        <h2 class="page-title">员工工时报表</h2>
        <p class="page-desc">
          按日期区间、部门、员工查询工时明细；展示工时汇总、按员工汇总与明细列表（数据来自 employee_work_hours）
        </p>
      </div>
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
        <el-form-item label="部门">
          <el-select
            v-model="filters.department"
            placeholder="全部"
            clearable
            filterable
            style="width: 160px"
            @change="handleDepartmentChange"
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
            style="width: 180px"
          >
            <el-option
              v-for="emp in employeeOptions"
              :key="emp.employee_no"
              :label="emp.employee_name"
              :value="emp.employee_no"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div class="summary-row">
      <el-card shadow="never" class="summary-card">
        <div class="summary-label">工时合计</div>
        <div class="summary-value">
          {{ formatHours(summary.workHoursSum) }}<span class="unit">h</span>
        </div>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <div class="summary-label">加班合计</div>
        <div class="summary-value">
          {{ formatHours(summary.overtimeHoursSum) }}<span class="unit">h</span>
        </div>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <div class="summary-label">涉及员工</div>
        <div class="summary-value">
          {{ summary.employeeCount }}<span class="unit">人</span>
        </div>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <div class="summary-label">明细条数</div>
        <div class="summary-value">
          {{ summary.recordCount }}<span class="unit">条</span>
        </div>
      </el-card>
    </div>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <span class="table-title">按员工汇总</span>
          <el-tag size="small" type="info">当前筛选条件下</el-tag>
        </div>
      </div>
      <el-table
        v-loading="summaryLoading"
        :data="summaryByEmployee"
        stripe
        border
        style="width: 100%"
        empty-text="暂无汇总数据"
      >
        <el-table-column prop="employee_name" label="员工" min-width="120" />
        <el-table-column prop="department" label="部门" min-width="140" />
        <el-table-column prop="work_hours" label="工时" width="110" align="right">
          <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
        </el-table-column>
        <el-table-column prop="overtime_hours" label="加班" width="110" align="right">
          <template #default="{ row }">{{ formatHours(row.overtime_hours) }}</template>
        </el-table-column>
        <el-table-column prop="record_count" label="明细条数" width="100" align="right" />
      </el-table>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <span class="table-title">员工工时报表</span>
          <el-tag size="small" type="info">明细列表</el-tag>
        </div>
        <div class="toolbar-right">
          <span class="sum-text">共 {{ total }} 条</span>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="employee_name" label="员工" min-width="120" />
        <el-table-column prop="department" label="部门" min-width="140" />
        <el-table-column prop="work_date" label="日期" width="130">
          <template #default="{ row }">{{ row.work_date || '—' }}</template>
        </el-table-column>
        <el-table-column prop="project_name" label="项目" min-width="140">
          <template #default="{ row }">{{ row.project_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="task_name" label="任务" min-width="140">
          <template #default="{ row }">{{ row.task_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="work_hours" label="工时" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
        </el-table-column>
        <el-table-column prop="overtime_hours" label="加班" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.overtime_hours) }}</template>
        </el-table-column>
        <el-table-column prop="approval_status" label="状态" width="100">
          <template #default="{ row }">{{ row.approval_status || '—' }}</template>
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
const summaryLoading = ref(false)
const items = ref([])
const summaryByEmployee = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const dateRange = ref(defaultDateRange())
const allEmployees = ref([])
const departmentOptions = ref([])

const filters = reactive({
  department: '',
  employeeNo: '',
})

const summary = reactive({
  workHoursSum: 0,
  overtimeHoursSum: 0,
  employeeCount: 0,
  recordCount: 0,
})

const employeeOptions = computed(() => {
  if (!filters.department) return allEmployees.value
  return allEmployees.value.filter((emp) => emp.department === filters.department)
})

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(1)
}

function handleDepartmentChange() {
  if (!filters.employeeNo) return
  const stillValid = employeeOptions.value.some((e) => e.employee_no === filters.employeeNo)
  if (!stillValid) filters.employeeNo = ''
}

async function loadFilters() {
  try {
    const resp = await fetchEmployeeWorkHourFilters()
    departmentOptions.value = resp.departments || []
    allEmployees.value = resp.employees || []
  } catch {
    departmentOptions.value = []
    allEmployees.value = []
  }
}

function applySummary(resp) {
  summary.workHoursSum = resp.work_hours_sum ?? 0
  summary.overtimeHoursSum = resp.overtime_hours_sum ?? 0
  summary.employeeCount = resp.employee_count ?? 0
  summary.recordCount = resp.record_count ?? 0
  summaryByEmployee.value = resp.summary_by_employee || []
}

async function loadReport() {
  loading.value = true
  summaryLoading.value = true
  try {
    const [dateFrom, dateTo] = dateRange.value || []
    const resp = await fetchEmployeeWorkHoursReport({
      page: page.value,
      pageSize: pageSize.value,
      dateFrom,
      dateTo,
      department: filters.department || undefined,
      employeeNo: filters.employeeNo || undefined,
      dimension: 'detail',
    })
    items.value = resp.items || []
    total.value = resp.total || 0
    applySummary(resp)
  } catch (err) {
    items.value = []
    summaryByEmployee.value = []
    total.value = 0
    ElMessage.error(err.message || '加载员工工时报表失败')
  } finally {
    loading.value = false
    summaryLoading.value = false
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
  page.value = 1
  loadReport()
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

.page-heading {
  margin-bottom: 16px;
}

.page-title {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.page-desc {
  margin: 0;
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
}

.search-form {
  margin-bottom: 0;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  border-radius: 8px;
}

.summary-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.summary-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  line-height: 1.2;
}

.summary-value .unit {
  font-size: 14px;
  font-weight: 400;
  color: #909399;
  margin-left: 4px;
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
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.table-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.sum-text {
  font-size: 13px;
  color: #606266;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 960px) {
  .summary-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
