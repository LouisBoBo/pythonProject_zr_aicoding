<template>
  <div class="work-hours-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="日期">
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
        <el-form-item label="所属部门">
          <el-select v-model="filters.department" placeholder="全部" clearable style="width: 140px">
            <el-option v-for="d in departmentOptions" :key="d" :label="d" :value="d" />
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
              v-for="emp in employeeOptions"
              :key="emp.employee_no"
              :label="`${emp.employee_name}（${emp.employee_no}）`"
              :value="emp.employee_no"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="项目名称">
          <el-select v-model="filters.projectName" placeholder="全部" clearable style="width: 140px">
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
          <el-radio-group v-model="dimension" size="small" @change="handleDimensionChange">
            <el-radio-button value="detail">明细</el-radio-button>
            <el-radio-button value="employee">按员工</el-radio-button>
            <el-radio-button value="project">按项目</el-radio-button>
            <el-radio-button value="department">按部门</el-radio-button>
          </el-radio-group>
        </div>
        <div class="toolbar-right">
          <span class="sum-text">工时合计（已通过） {{ formatHours(workHoursSum) }}</span>
          <span class="sum-text">加班合计（已通过） {{ formatHours(overtimeHoursSum) }}</span>
          <el-button type="primary" @click="openCreateDialog">新增工时</el-button>
          <template v-if="dimension === 'detail'">
            <el-button
              type="success"
              :disabled="!selectedPendingIds.length"
              @click="handleBatchApproval('approved')"
            >
              批量通过
            </el-button>
            <el-button
              type="warning"
              :disabled="!selectedPendingIds.length"
              @click="handleBatchApproval('rejected')"
            >
              批量驳回
            </el-button>
          </template>
          <el-button :icon="Download" @click="handleExport">导出</el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="items"
        stripe
        border
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column
          v-if="dimension === 'detail'"
          type="selection"
          width="48"
          :selectable="rowSelectable"
        />
        <el-table-column v-if="showCol('status')" prop="status" label="状态" width="90">
          <template #default="{ row }">{{ row.status || '—' }}</template>
        </el-table-column>
        <el-table-column
          v-if="showCol('employee_name')"
          prop="employee_name"
          label="员工姓名"
          min-width="100"
        />
        <el-table-column v-if="showCol('employee_no')" prop="employee_no" label="工号" width="100" />
        <el-table-column
          v-if="showCol('department')"
          prop="department"
          label="所属部门"
          min-width="120"
        />
        <el-table-column v-if="showCol('project_name')" prop="project_name" label="项目名称" min-width="120">
          <template #default="{ row }">{{ row.project_name || '—' }}</template>
        </el-table-column>
        <el-table-column v-if="showCol('task_name')" prop="task_name" label="任务名称" min-width="120">
          <template #default="{ row }">{{ row.task_name || '—' }}</template>
        </el-table-column>
        <el-table-column v-if="showCol('work_date')" prop="work_date" label="日期" width="120">
          <template #default="{ row }">{{ row.work_date || '—' }}</template>
        </el-table-column>
        <el-table-column v-if="showCol('shift_type')" prop="shift_type" label="班别" width="80">
          <template #default="{ row }">{{ row.shift_type || '—' }}</template>
        </el-table-column>
        <el-table-column prop="work_hours" label="工时数" width="90" align="right">
          <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
        </el-table-column>
        <el-table-column prop="overtime_hours" label="加班工时" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.overtime_hours) }}</template>
        </el-table-column>
        <el-table-column
          v-if="showCol('record_count')"
          prop="record_count"
          label="明细条数"
          width="100"
          align="right"
        />
        <el-table-column v-if="showCol('approval_status')" prop="approval_status" label="审批" width="90">
          <template #default="{ row }">{{ row.approval_status || '—' }}</template>
        </el-table-column>
        <el-table-column v-if="dimension === 'detail'" label="审批操作" width="150" fixed="right">
          <template #default="{ row }">
            <template v-if="row.approval_status === '待审批'">
              <el-button link type="success" size="small" @click="handleRowApproval(row, 'approved')">
                通过
              </el-button>
              <el-button link type="warning" size="small" @click="handleRowApproval(row, 'rejected')">
                驳回
              </el-button>
            </template>
            <span v-else class="muted">—</span>
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

    <el-dialog v-model="createVisible" title="新增工时" width="520px" destroy-on-close>
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="96px">
        <el-form-item label="工号" prop="employee_no">
          <el-input v-model="createForm.employee_no" maxlength="20" />
        </el-form-item>
        <el-form-item label="员工姓名" prop="employee_name">
          <el-input v-model="createForm.employee_name" maxlength="50" />
        </el-form-item>
        <el-form-item label="所属部门" prop="department">
          <el-input v-model="createForm.department" maxlength="50" />
        </el-form-item>
        <el-form-item label="项目名称" prop="project_name">
          <el-input v-model="createForm.project_name" maxlength="100" />
        </el-form-item>
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="createForm.task_name" maxlength="100" />
        </el-form-item>
        <el-form-item label="日期" prop="work_date">
          <el-date-picker
            v-model="createForm.work_date"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="班别" prop="shift_type">
          <el-select v-model="createForm.shift_type" style="width: 100%">
            <el-option label="白班" value="day" />
            <el-option label="晚班" value="night" />
          </el-select>
        </el-form-item>
        <el-form-item label="工时数" prop="work_hours">
          <el-input-number v-model="createForm.work_hours" :min="0" :max="24" :step="0.5" style="width: 100%" />
        </el-form-item>
        <el-form-item label="加班工时" prop="overtime_hours">
          <el-input-number
            v-model="createForm.overtime_hours"
            :min="0"
            :max="24"
            :step="0.5"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createSubmitting" @click="submitCreate">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchApproveEmployeeWorkHours,
  createEmployeeWorkHour,
  exportEmployeeWorkHoursReport,
  fetchEmployeeWorkHourFilters,
  fetchEmployeeWorkHoursReport,
} from '../../api/reports/employeeWorkHours.js'

const DIMENSION_COLS = {
  detail: [
    'status',
    'employee_name',
    'employee_no',
    'department',
    'project_name',
    'task_name',
    'work_date',
    'shift_type',
    'approval_status',
  ],
  employee: [
    'status',
    'employee_name',
    'employee_no',
    'department',
    'record_count',
    'approval_status',
  ],
  project: ['status', 'project_name', 'record_count', 'approval_status'],
  department: ['status', 'department', 'record_count', 'approval_status'],
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
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const workHoursSum = ref(0)
const overtimeHoursSum = ref(0)
const dimension = ref('detail')
const dateRange = ref(defaultDateRange())
const departmentOptions = ref([])
const employeeOptions = ref([])
const projectOptions = ref([])
const selectedRows = ref([])

const filters = reactive({
  department: '',
  employeeNo: '',
  projectName: '',
  shiftType: '',
  approvalStatus: '',
})

const createVisible = ref(false)
const createSubmitting = ref(false)
const createFormRef = ref(null)
const createForm = reactive({
  employee_no: '',
  employee_name: '',
  department: '',
  project_name: '',
  task_name: '',
  work_date: '',
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

const dateFrom = computed(() => (dateRange.value && dateRange.value[0]) || '')
const dateTo = computed(() => (dateRange.value && dateRange.value[1]) || '')

const selectedPendingIds = computed(() =>
  selectedRows.value.filter((r) => r.approval_status === '待审批' && r.id).map((r) => r.id),
)

function showCol(key) {
  return (DIMENSION_COLS[dimension.value] || []).includes(key)
}

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(1)
}

function rowSelectable(row) {
  return row.approval_status === '待审批'
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

/** @param {string|undefined} approval_status 审批筛选 pending / approved / rejected */
function queryParams(approval_status = filters.approvalStatus || undefined) {
  return {
    dateFrom: dateFrom.value,
    dateTo: dateTo.value,
    department: filters.department || undefined,
    employeeNo: filters.employeeNo || undefined,
    projectName: filters.projectName || undefined,
    shiftType: filters.shiftType || undefined,
    approval_status,
    approvalStatus: approval_status,
    dimension: dimension.value,
  }
}

async function loadFilters() {
  try {
    const resp = await fetchEmployeeWorkHourFilters()
    departmentOptions.value = resp.departments || []
    employeeOptions.value = resp.employees || []
    projectOptions.value = resp.projects || []
  } catch {
    departmentOptions.value = []
    employeeOptions.value = []
    projectOptions.value = []
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
    selectedRows.value = []
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
  dateRange.value = defaultDateRange()
  filters.department = ''
  filters.employeeNo = ''
  filters.projectName = ''
  filters.shiftType = ''
  filters.approvalStatus = ''
  page.value = 1
  loadReport()
}

function handleDimensionChange() {
  page.value = 1
  loadReport()
}

function openCreateDialog() {
  createVisible.value = true
}

async function submitCreate() {
  if (!createFormRef.value) return
  try {
    await createFormRef.value.validate()
  } catch {
    return
  }
  createSubmitting.value = true
  try {
    await createEmployeeWorkHour({
      ...createForm,
      approval_status: 'pending',
    })
    ElMessage.success('工时已提交，待审批')
    createVisible.value = false
    await loadFilters()
    await loadReport()
  } catch (err) {
    ElMessage.error(err.message || '新增工时失败')
  } finally {
    createSubmitting.value = false
  }
}

async function runBatchApproval(ids, approval_status, label) {
  if (!ids.length) return
  try {
    await ElMessageBox.confirm(`确认${label}选中的 ${ids.length} 条记录？`, '审批确认', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    const resp = await batchApproveEmployeeWorkHours({ ids, approvalStatus: approval_status })
    ElMessage.success(`已${label} ${resp.updated || 0} 条`)
    await loadReport()
  } catch (err) {
    ElMessage.error(err.message || `${label}失败`)
  }
}

function handleBatchApproval(approvalStatus) {
  const label = approvalStatus === 'approved' ? '通过' : '驳回'
  runBatchApproval(selectedPendingIds.value, approvalStatus, label)
}

function handleRowApproval(row, approvalStatus) {
  if (!row.id) return
  const label = approvalStatus === 'approved' ? '通过' : '驳回'
  runBatchApproval([row.id], approvalStatus, label)
}

async function handleExport() {
  try {
    const { approvalStatus: _omit, approval_status: _omit2, ...exportQuery } = queryParams()
    const blob = await exportEmployeeWorkHoursReport(exportQuery)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `employee_work_hours_${Date.now()}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出已开始（默认仅已通过数据）')
  } catch (err) {
    ElMessage.error(err.message || '导出失败')
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

.muted {
  color: var(--el-text-color-secondary);
}
</style>
