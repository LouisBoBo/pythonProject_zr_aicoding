<template>
  <div class="work-hours-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="searchForm" inline class="search-form">
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="searchForm.dateRange"
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
            v-model="searchForm.department"
            placeholder="全部"
            clearable
            filterable
            style="width: 150px"
          >
            <el-option v-for="dept in filterOptions.departments" :key="dept" :label="dept" :value="dept" />
          </el-select>
        </el-form-item>
        <el-form-item label="工号">
          <el-select
            v-model="searchForm.employeeNo"
            placeholder="全部"
            clearable
            filterable
            style="width: 130px"
          >
            <el-option
              v-for="emp in filterOptions.employees"
              :key="emp.employee_no"
              :label="emp.employee_no"
              :value="emp.employee_no"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="项目">
          <el-select
            v-model="searchForm.projectName"
            placeholder="全部"
            clearable
            filterable
            style="width: 150px"
          >
            <el-option v-for="p in filterOptions.projects" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="班别">
          <el-select v-model="searchForm.shiftType" placeholder="全部" clearable style="width: 110px">
            <el-option label="全部" value="" />
            <el-option label="白班" value="day" />
            <el-option label="晚班" value="night" />
          </el-select>
        </el-form-item>
        <el-form-item label="审批">
          <el-select v-model="searchForm.approvalStatus" placeholder="全部" clearable style="width: 120px">
            <el-option label="全部" value="" />
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="全部" value="" />
            <el-option label="待生效" value="pending_effect" />
            <el-option label="已生效" value="effective" />
            <el-option label="已作废" value="void" />
          </el-select>
        </el-form-item>
        <el-form-item label="展示">
          <el-select v-model="searchForm.dimension" style="width: 130px">
            <el-option label="明细" value="detail" />
            <el-option label="按员工汇总" value="employee" />
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
        <span class="table-title">员工工时报表</span>
        <span v-if="total > 0" class="sum-text">
          工时合计 {{ formatHours(workHoursSum) }} · 加班合计 {{ formatHours(overtimeHoursSum) }}
        </span>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="employee_name" label="员工" min-width="100" />
        <!-- 标注：工号列位于「员工」与「部门」之间 -->
        <el-table-column prop="employee_no" label="工号" width="110" />
        <el-table-column prop="department" label="部门" min-width="120" />
        <el-table-column v-if="showDetailColumns" prop="project_name" label="项目" min-width="120">
          <template #default="{ row }">{{ row.project_name || '—' }}</template>
        </el-table-column>
        <el-table-column v-if="showDetailColumns" prop="task_name" label="任务" min-width="120">
          <template #default="{ row }">{{ row.task_name || '—' }}</template>
        </el-table-column>
        <el-table-column v-if="showDetailColumns" prop="work_date" label="日期" width="120">
          <template #default="{ row }">{{ row.work_date || '—' }}</template>
        </el-table-column>
        <!-- 标注：第7列「班别」与第8列「工时」衔接（班别/工时/加班/审批状态区） -->
        <el-table-column v-if="showDetailColumns" prop="shift_type" label="班别" width="80">
          <template #default="{ row }">{{ row.shift_type || '—' }}</template>
        </el-table-column>
        <el-table-column prop="work_hours" label="工时" width="90" align="right">
          <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
        </el-table-column>
        <el-table-column prop="overtime_hours" label="加班工时" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.overtime_hours) }}</template>
        </el-table-column>
        <el-table-column prop="approval_status" label="审批" width="90">
          <template #default="{ row }">{{ row.approval_status || '—' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">{{ row.status || '—' }}</template>
        </el-table-column>
      </el-table>

      <div v-if="total > 0" class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="loadReport"
          @current-change="loadReport"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
/** 员工工时报表（路由组件文件名为 MaterialInboundListView.vue） */
defineOptions({ name: 'EmployeeWorkHoursReportWarehouseView' })

import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { appendPagination, authFetch } from '../../api/http.js'

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
const overtimeHoursSum = ref(0)
const workHoursSum = ref(0)
const filterOptions = reactive({
  departments: [],
  employees: [],
  projects: [],
})

const searchForm = reactive({
  dateRange: defaultDateRange(),
  department: '',
  employeeNo: '',
  projectName: '',
  shiftType: '',
  approvalStatus: '',
  status: '',
  dimension: 'detail',
})

/** 明细维度展示项目/任务/日期/班别列 */
const showDetailColumns = computed(() => searchForm.dimension === 'detail')

function queryParams() {
  const dr = searchForm.dateRange
  return {
    date_from: (dr && dr[0]) || undefined,
    date_to: (dr && dr[1]) || undefined,
    department: searchForm.department || undefined,
    employee_no: searchForm.employeeNo || undefined,
    project_name: searchForm.projectName || undefined,
    shift_type: searchForm.shiftType || undefined,
    approval_status: searchForm.approvalStatus || undefined,
    status: searchForm.status || undefined,
    dimension: searchForm.dimension || 'detail',
  }
}

function formatHours(value) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(1)
}

async function fetchEmployeeWorkHoursFromWarehouse({ page: p, pageSize: size, ...rest } = {}) {
  const params = new URLSearchParams()
  appendPagination(params, { page: p, pageSize: size })
  Object.entries(rest).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') params.set(key, String(val))
  })
  return authFetch(`/api/warehouse/employee-work-hours?${params.toString()}`)
}

async function loadFilters() {
  try {
    const resp = await authFetch('/api/reports/employee-work-hours/filters')
    filterOptions.departments = resp.departments || []
    filterOptions.employees = resp.employees || []
    filterOptions.projects = resp.projects || []
  } catch (err) {
    filterOptions.departments = []
    filterOptions.employees = []
    filterOptions.projects = []
    ElMessage.warning(err?.message || '加载筛选选项失败')
  }
}

async function loadReport() {
  loading.value = true
  try {
    const resp = await fetchEmployeeWorkHoursFromWarehouse({
      page: page.value,
      pageSize: pageSize.value,
      ...queryParams(),
    })
    items.value = resp.items || []
    total.value = resp.total || 0
    workHoursSum.value = resp.work_hours_sum || 0
    overtimeHoursSum.value = resp.overtime_hours_sum || 0
  } catch (err) {
    items.value = []
    total.value = 0
    workHoursSum.value = 0
    overtimeHoursSum.value = 0
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
  searchForm.dateRange = defaultDateRange()
  searchForm.department = ''
  searchForm.employeeNo = ''
  searchForm.projectName = ''
  searchForm.shiftType = ''
  searchForm.approvalStatus = ''
  searchForm.status = ''
  searchForm.dimension = 'detail'
  page.value = 1
  loadReport()
}

onMounted(() => {
  loadFilters()
  loadReport()
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
  gap: 8px;
  margin-bottom: 12px;
}

.table-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
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
