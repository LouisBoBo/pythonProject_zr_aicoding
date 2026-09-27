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
            style="width: 150px"
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
            style="width: 180px"
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
            style="width: 150px"
          >
            <el-option v-for="p in filterOptions.projects" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="班别">
          <el-select v-model="filters.shiftType" placeholder="全部" clearable style="width: 110px">
            <el-option label="白班" value="day" />
            <el-option label="晚班" value="night" />
          </el-select>
        </el-form-item>
        <el-form-item label="统计维度">
          <el-select v-model="filters.dimension" style="width: 160px" @change="handleDimensionChange">
            <el-option label="明细" value="detail" />
            <el-option label="按员工汇总" value="employee" />
            <el-option label="按员工+日期" value="employee_date" />
            <el-option label="按员工+月份" value="employee_month" />
            <el-option label="按项目" value="project" />
            <el-option label="按部门" value="department" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
          <el-button type="success" @click="openCreateDialog">新增工时</el-button>
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
          <span class="sum-text">工时合计 {{ formatHours(workHoursSum) }}</span>
          <span class="sum-text">加班合计 {{ formatHours(overtimeHoursSum) }}</span>
          <el-button :icon="Download" :loading="exporting" @click="handleExport">导出 Excel</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="employee_name" label="员工" min-width="100" />
        <el-table-column prop="employee_no" label="工号" width="110" />
        <el-table-column prop="department" label="部门" min-width="120" />
        <el-table-column
          v-if="showProjectColumn"
          prop="project_name"
          label="项目"
          min-width="120"
        >
          <template #default="{ row }">{{ row.project_name || '—' }}</template>
        </el-table-column>
        <el-table-column
          v-if="showTaskColumn"
          prop="task_name"
          label="任务"
          min-width="120"
        >
          <template #default="{ row }">{{ row.task_name || '—' }}</template>
        </el-table-column>
        <el-table-column
          v-if="showDateColumn"
          prop="work_date"
          label="日期"
          width="120"
        >
          <template #default="{ row }">{{ row.work_date || '—' }}</template>
        </el-table-column>
        <el-table-column
          v-if="showMonthColumn"
          prop="work_month"
          label="月份"
          width="100"
        >
          <template #default="{ row }">{{ row.work_month || '—' }}</template>
        </el-table-column>
        <el-table-column
          v-if="showShiftColumn"
          prop="shift_type"
          label="班别"
          width="80"
        >
          <template #default="{ row }">{{ row.shift_type || '—' }}</template>
        </el-table-column>
        <el-table-column prop="work_hours" label="工时" width="90" align="right">
          <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
        </el-table-column>
        <el-table-column prop="overtime_hours" label="加班工时" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.overtime_hours) }}</template>
        </el-table-column>
        <el-table-column
          v-if="showRecordCountColumn"
          prop="record_count"
          label="明细条数"
          width="100"
          align="right"
        />
        <el-table-column
          v-if="showApprovalColumn"
          prop="approval_status"
          label="审批/状态"
          width="100"
        >
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

    <el-dialog v-model="createVisible" title="新增员工工时" width="520px" destroy-on-close>
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="90px">
        <el-form-item label="工号" prop="employee_no">
          <el-input v-model="createForm.employee_no" maxlength="20" />
        </el-form-item>
        <el-form-item label="姓名" prop="employee_name">
          <el-input v-model="createForm.employee_name" maxlength="50" />
        </el-form-item>
        <el-form-item label="部门" prop="department">
          <el-input v-model="createForm.department" maxlength="50" />
        </el-form-item>
        <el-form-item label="项目" prop="project_name">
          <el-input v-model="createForm.project_name" maxlength="100" />
        </el-form-item>
        <el-form-item label="任务" prop="task_name">
          <el-input v-model="createForm.task_name" maxlength="100" />
        </el-form-item>
        <el-form-item label="工作日期" prop="work_date">
          <el-date-picker
            v-model="createForm.work_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="班别" prop="shift_type">
          <el-radio-group v-model="createForm.shift_type">
            <el-radio value="day">白班</el-radio>
            <el-radio value="night">晚班</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="工时" prop="work_hours">
          <el-input-number v-model="createForm.work_hours" :min="0" :max="24" :step="0.5" style="width: 100%" />
        </el-form-item>
        <el-form-item label="加班工时" prop="overtime_hours">
          <el-input-number v-model="createForm.overtime_hours" :min="0" :max="24" :step="0.5" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  createEmployeeWorkHour,
  exportEmployeeWorkHoursReport,
  fetchEmployeeWorkHourFilters,
  fetchEmployeeWorkHoursReport,
} from '../../api/reports/employeeWorkHours.js'

const DIMENSION_LABELS = {
  detail: '明细列表',
  employee: '按员工汇总',
  employee_date: '按员工+日期',
  employee_month: '按员工+月份',
  project: '按项目汇总',
  department: '按部门汇总',
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
  return [fmt(start), fmt(end)]
}

function todayStr() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const loading = ref(false)
const exporting = ref(false)
const creating = ref(false)
const createVisible = ref(false)
const createFormRef = ref(null)
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
  shiftType: '',
  dimension: 'detail',
})

const createForm = reactive({
  employee_no: '',
  employee_name: '',
  department: '',
  project_name: '',
  task_name: '',
  work_date: todayStr(),
  shift_type: 'day',
  work_hours: 8,
  overtime_hours: 0,
})

const createRules = {
  employee_no: [{ required: true, message: '请输入工号', trigger: 'blur' }],
  employee_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  department: [{ required: true, message: '请输入部门', trigger: 'blur' }],
  project_name: [{ required: true, message: '请输入项目', trigger: 'blur' }],
  task_name: [{ required: true, message: '请输入任务', trigger: 'blur' }],
  work_date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  work_hours: [{ required: true, message: '请输入工时', trigger: 'change' }],
}

const dimensionLabel = computed(() => DIMENSION_LABELS[filters.dimension] || filters.dimension)
const showProjectColumn = computed(() => ['detail', 'project'].includes(filters.dimension))
const showTaskColumn = computed(() => filters.dimension === 'detail')
const showDateColumn = computed(() => ['detail', 'employee_date'].includes(filters.dimension))
const showMonthColumn = computed(() => filters.dimension === 'employee_month')
const showShiftColumn = computed(() => filters.dimension === 'detail')
const showRecordCountColumn = computed(() => filters.dimension !== 'detail')
const showApprovalColumn = computed(() => true)

function queryParams() {
  return {
    dateFrom: (dateRange.value && dateRange.value[0]) || undefined,
    dateTo: (dateRange.value && dateRange.value[1]) || undefined,
    department: filters.department || undefined,
    employeeNo: filters.employeeNo || undefined,
    projectName: filters.projectName || undefined,
    shiftType: filters.shiftType || undefined,
    dimension: filters.dimension,
  }
}

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(1)
}

function handleDimensionChange() {
  page.value = 1
  loadReport()
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
    const resp = await fetchEmployeeWorkHoursReport({
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
  filters.department = ''
  filters.employeeNo = ''
  filters.projectName = ''
  filters.shiftType = ''
  filters.dimension = 'detail'
  dateRange.value = defaultDateRange()
  page.value = 1
  loadReport()
}

function openCreateDialog() {
  createForm.work_date = todayStr()
  createVisible.value = true
}

async function submitCreate() {
  if (!createFormRef.value) return
  try {
    await createFormRef.value.validate()
  } catch {
    return
  }
  creating.value = true
  try {
    await createEmployeeWorkHour({ ...createForm })
    ElMessage.success('新增工时成功')
    createVisible.value = false
    await loadFilters()
    await loadReport()
  } catch (err) {
    ElMessage.error(err.message || '新增失败')
  } finally {
    creating.value = false
  }
}

async function handleExport() {
  exporting.value = true
  try {
    const blob = await exportEmployeeWorkHoursReport(queryParams())
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `employee_work_hours_${Date.now()}.xlsx`
    a.click()
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
  gap: 8px;
  margin-bottom: 12px;
}

.toolbar-left,
.toolbar-right {
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
