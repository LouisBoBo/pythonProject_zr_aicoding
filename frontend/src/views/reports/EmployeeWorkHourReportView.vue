<template>
  <div class="employee-work-hour-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="工作日期">
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
            style="width: 140px"
          >
            <el-option v-for="d in departmentOptions" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="工号">
          <el-input v-model="filters.employeeNo" placeholder="工号" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="项目">
          <el-select
            v-model="filters.projectName"
            placeholder="全部"
            clearable
            filterable
            style="width: 160px"
          >
            <el-option v-for="p in projectOptions" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="班别">
          <el-select v-model="filters.shiftType" placeholder="全部" clearable style="width: 100px">
            <el-option label="白班" value="day" />
            <el-option label="晚班" value="night" />
          </el-select>
        </el-form-item>
        <el-form-item label="审批">
          <el-select v-model="filters.approvalStatus" placeholder="全部" clearable style="width: 110px">
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
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
          <el-tag size="small" type="info">明细维度</el-tag>
        </div>
        <div class="toolbar-right">
          <span class="sum-text">工时合计 {{ formatHours(workHoursSum) }}</span>
          <span class="sum-text">加班合计 {{ formatHours(overtimeHoursSum) }}</span>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="work_date" label="日期" width="120">
          <template #default="{ row }">{{ row.work_date || '—' }}</template>
        </el-table-column>
        <el-table-column prop="employee_no" label="工号" width="100" />
        <el-table-column prop="employee_name" label="员工姓名" min-width="100" />
        <el-table-column prop="department" label="所属部门" min-width="110" />
        <el-table-column prop="project_name" label="项目名称" min-width="120">
          <template #default="{ row }">{{ row.project_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="task_name" label="任务名称" min-width="120">
          <template #default="{ row }">{{ row.task_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="shift_type" label="班别" width="80" align="center">
          <template #default="{ row }">{{ row.shift_type || '—' }}</template>
        </el-table-column>
        <el-table-column prop="work_hours" label="工时数" width="90" align="right">
          <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
        </el-table-column>
        <el-table-column prop="overtime_hours" label="加班工时" width="90" align="right">
          <template #default="{ row }">{{ formatHours(row.overtime_hours) }}</template>
        </el-table-column>
        <el-table-column prop="approval_status" label="审批" width="90" align="center">
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
  fetchEmployeeWorkHourReport,
} from '../../api/reports/employeeWorkHours.js'

function defaultDateRange() {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 29)
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
const departmentOptions = ref([])
const projectOptions = ref([])
const workHoursSum = ref(0)
const overtimeHoursSum = ref(0)
const dateRange = ref(defaultDateRange())

const filters = reactive({
  department: '',
  employeeNo: '',
  projectName: '',
  shiftType: '',
  approvalStatus: '',
})

const dateFrom = computed(() => (dateRange.value && dateRange.value[0]) || '')
const dateTo = computed(() => (dateRange.value && dateRange.value[1]) || '')

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
}

async function loadFilters() {
  try {
    const resp = await fetchEmployeeWorkHourFilters()
    departmentOptions.value = resp.departments || []
    projectOptions.value = resp.projects || []
  } catch {
    departmentOptions.value = []
    projectOptions.value = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const resp = await fetchEmployeeWorkHourReport({
      page: page.value,
      pageSize: pageSize.value,
      dateFrom: dateFrom.value || undefined,
      dateTo: dateTo.value || undefined,
      department: filters.department || undefined,
      employeeNo: filters.employeeNo || undefined,
      projectName: filters.projectName || undefined,
      shiftType: filters.shiftType || undefined,
      approvalStatus: filters.approvalStatus || undefined,
      dimension: 'detail',
    })
    items.value = resp.items || []
    total.value = resp.total || 0
    workHoursSum.value = resp.work_hours_sum || 0
    overtimeHoursSum.value = resp.overtime_hours_sum || 0
  } catch (err) {
    ElMessage.error(err.message || '加载报表失败')
    items.value = []
    total.value = 0
    workHoursSum.value = 0
    overtimeHoursSum.value = 0
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
  filters.department = ''
  filters.employeeNo = ''
  filters.projectName = ''
  filters.shiftType = ''
  filters.approvalStatus = ''
  page.value = 1
  loadReport()
}

onMounted(async () => {
  await loadFilters()
  await loadReport()
})
</script>

<style scoped>
.employee-work-hour-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.search-card :deep(.el-card__body) {
  padding-bottom: 4px;
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

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.table-title {
  font-weight: 600;
  font-size: 15px;
}

.sum-text {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
