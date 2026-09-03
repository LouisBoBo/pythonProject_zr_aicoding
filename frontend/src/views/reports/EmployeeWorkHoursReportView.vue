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
            style="width: 140px"
          >
            <el-option v-for="dept in filterOptions.departments" :key="dept" :label="dept" :value="dept" />
          </el-select>
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
              v-for="emp in filterOptions.employees"
              :key="emp.employee_no"
              :label="`${emp.employee_name}（${emp.employee_no}）`"
              :value="emp.employee_no"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="项目">
          <el-select
            v-model="filters.projectName"
            placeholder="全部"
            clearable
            filterable
            style="width: 160px"
          >
            <el-option v-for="proj in filterOptions.projects" :key="proj" :label="proj" :value="proj" />
          </el-select>
        </el-form-item>
        <el-form-item label="统计维度">
          <el-select v-model="filters.dimension" style="width: 180px" @change="handleDimensionChange">
            <el-option label="明细（员工+任务）" value="detail" />
            <el-option label="按员工+日期" value="employee_date" />
            <el-option label="按员工+月份" value="employee_month" />
            <el-option label="按项目汇总" value="project" />
            <el-option label="按部门汇总" value="department" />
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
          <el-tag size="small" type="info">{{ dimensionLabel }}</el-tag>
        </div>
        <div class="toolbar-right">
          <span class="sum-text">工时合计 {{ workHoursSum }}</span>
          <span class="sum-text">加班合计 {{ overtimeHoursSum }}</span>
          <el-button :icon="Download" :loading="exporting" @click="handleExport">导出 Excel</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column
          v-if="showEmployeeColumns"
          prop="employee_name"
          label="员工姓名"
          min-width="100"
        />
        <el-table-column
          v-if="showEmployeeColumns"
          prop="employee_no"
          label="工号"
          width="100"
        />
        <el-table-column
          v-if="showDepartmentColumn"
          prop="department"
          label="所属部门"
          min-width="110"
        />
        <el-table-column
          v-if="showProjectColumn"
          prop="project_name"
          label="项目名称"
          min-width="140"
        >
          <template #default="{ row }">{{ row.project_name || '—' }}</template>
        </el-table-column>
        <el-table-column
          v-if="showTaskColumn"
          prop="task_name"
          label="任务名称"
          min-width="120"
        >
          <template #default="{ row }">{{ row.task_name || '—' }}</template>
        </el-table-column>
        <el-table-column
          v-if="showDateColumn"
          prop="work_date"
          label="日期"
          width="120"
        />
        <el-table-column
          v-if="showMonthColumn"
          prop="work_month"
          label="月份"
          width="100"
        />
        <el-table-column prop="work_hours" label="工时数" width="90" align="right">
          <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
        </el-table-column>
        <el-table-column prop="overtime_hours" label="加班工时" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.overtime_hours) }}</template>
        </el-table-column>
        <el-table-column
          v-if="showRecordCount"
          prop="record_count"
          label="明细条数"
          width="100"
          align="right"
        />
        <el-table-column prop="approval_status" label="审批/状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.approval_status === '已通过'" size="small" type="success">已通过</el-tag>
            <el-tag v-else-if="row.approval_status === '待审批'" size="small" type="warning">待审批</el-tag>
            <el-tag v-else-if="row.approval_status === '已驳回'" size="small" type="danger">已驳回</el-tag>
            <span v-else>{{ row.approval_status || '—' }}</span>
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
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  exportEmployeeWorkHoursReport,
  fetchEmployeeWorkHourFilters,
  fetchEmployeeWorkHoursReport,
} from '../../api/reports'

const DIMENSION_LABELS = {
  detail: '明细（员工+任务）',
  employee_date: '按员工+日期',
  employee_month: '按员工+月份',
  project: '按项目汇总',
  department: '按部门汇总',
}

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
const exporting = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const workHoursSum = ref(0)
const overtimeHoursSum = ref(0)
const dateRange = ref(defaultDateRange())
const filterOptions = reactive({
  departments: [],
  employees: [],
  projects: [],
})

const filters = reactive({
  department: '',
  employeeNo: '',
  projectName: '',
  dimension: 'detail',
})

const dateFrom = computed(() => (dateRange.value && dateRange.value[0]) || '')
const dateTo = computed(() => (dateRange.value && dateRange.value[1]) || '')
const dimensionLabel = computed(() => DIMENSION_LABELS[filters.dimension] || filters.dimension)

const showEmployeeColumns = computed(() =>
  ['detail', 'employee_date', 'employee_month'].includes(filters.dimension),
)
const showDepartmentColumn = computed(() =>
  ['detail', 'employee_date', 'employee_month', 'department'].includes(filters.dimension),
)
const showProjectColumn = computed(
  () => filters.dimension === 'detail' || filters.dimension === 'project',
)
const showTaskColumn = computed(() => filters.dimension === 'detail')
const showDateColumn = computed(
  () => filters.dimension === 'detail' || filters.dimension === 'employee_date',
)
const showMonthColumn = computed(() => filters.dimension === 'employee_month')
const showRecordCount = computed(() => filters.dimension !== 'detail')

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
}

function buildQueryParams() {
  return {
    page: page.value,
    pageSize: pageSize.value,
    dateFrom: dateFrom.value || undefined,
    dateTo: dateTo.value || undefined,
    department: filters.department || undefined,
    employeeNo: filters.employeeNo || undefined,
    projectName: filters.projectName || undefined,
    dimension: filters.dimension,
  }
}

async function loadFilters() {
  try {
    const resp = await fetchEmployeeWorkHourFilters()
    filterOptions.departments = resp.departments || []
    filterOptions.employees = resp.employees || []
    filterOptions.projects = resp.projects || []
  } catch {
    filterOptions.departments = []
    filterOptions.employees = []
    filterOptions.projects = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const resp = await fetchEmployeeWorkHoursReport(buildQueryParams())
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

function handleDimensionChange() {
  page.value = 1
  loadReport()
}

function handleReset() {
  dateRange.value = defaultDateRange()
  filters.department = ''
  filters.employeeNo = ''
  filters.projectName = ''
  filters.dimension = 'detail'
  page.value = 1
  loadReport()
}

async function handleExport() {
  exporting.value = true
  try {
    const { page: _p, pageSize: _s, ...exportParams } = buildQueryParams()
    const blob = await exportEmployeeWorkHoursReport(exportParams)
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `员工工时报表_${new Date().toISOString().slice(0, 10)}.xlsx`
    link.click()
    URL.revokeObjectURL(link.href)
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
