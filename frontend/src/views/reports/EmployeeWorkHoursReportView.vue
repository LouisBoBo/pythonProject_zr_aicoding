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
            <el-option
              v-for="dept in departmentOptions"
              :key="dept"
              :label="dept"
              :value="dept"
            />
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
              :label="`${emp.employee_name} (${emp.employee_no})`"
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
            style="width: 180px"
          >
            <el-option v-for="proj in projectOptions" :key="proj" :label="proj" :value="proj" />
          </el-select>
        </el-form-item>
        <el-form-item label="视图">
          <el-radio-group v-model="viewMode" @change="handleViewModeChange">
            <el-radio-button value="detail">明细</el-radio-button>
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
            {{ viewMode === 'employee' ? '按员工汇总工时合计' : '明细列表' }}
          </el-tag>
        </div>
        <div class="toolbar-right">
          <span class="sum-text">工时合计 {{ formatHours(workHoursSum) }}</span>
          <span class="sum-text">加班合计 {{ formatHours(overtimeHoursSum) }}</span>
          <el-button type="primary" :icon="Plus" @click="openCreate">新增工时</el-button>
          <el-button :icon="Download" @click="handleExport">导出</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="employee_name" label="员工" min-width="120" />
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="department" label="部门" min-width="140" />
        <el-table-column
          v-if="viewMode === 'detail'"
          prop="work_date"
          label="日期"
          width="130"
        >
          <template #default="{ row }">{{ row.work_date || '—' }}</template>
        </el-table-column>
        <el-table-column
          v-if="viewMode === 'detail'"
          prop="project_name"
          label="项目"
          min-width="120"
        >
          <template #default="{ row }">{{ row.project_name || '—' }}</template>
        </el-table-column>
        <el-table-column
          v-if="viewMode === 'detail'"
          prop="task_name"
          label="任务"
          min-width="120"
        >
          <template #default="{ row }">{{ row.task_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="work_hours" label="工时" width="120" align="right">
          <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
        </el-table-column>
        <el-table-column prop="overtime_hours" label="加班" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.overtime_hours) }}</template>
        </el-table-column>
        <el-table-column
          v-if="viewMode === 'detail'"
          prop="approval_status"
          label="状态"
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

    <el-dialog
      v-model="createVisible"
      title="新增工时"
      width="520px"
      destroy-on-close
      @closed="resetCreateForm"
    >
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="88px">
        <el-form-item label="员工" prop="employeeNo">
          <el-select
            v-model="createForm.employeeNo"
            placeholder="选择或输入工号"
            filterable
            allow-create
            default-first-option
            style="width: 100%"
            @change="onCreateEmployeeChange"
          >
            <el-option
              v-for="emp in employeeOptions"
              :key="emp.employee_no"
              :label="`${emp.employee_name} (${emp.employee_no})`"
              :value="emp.employee_no"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="姓名" prop="employeeName">
          <el-input v-model="createForm.employeeName" placeholder="员工姓名" />
        </el-form-item>
        <el-form-item label="部门" prop="department">
          <el-input v-model="createForm.department" placeholder="所属部门" />
        </el-form-item>
        <el-form-item label="项目" prop="projectName">
          <el-select
            v-model="createForm.projectName"
            placeholder="项目"
            filterable
            allow-create
            default-first-option
            style="width: 100%"
          >
            <el-option v-for="proj in projectOptions" :key="proj" :label="proj" :value="proj" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务" prop="taskName">
          <el-input v-model="createForm.taskName" placeholder="任务名称" />
        </el-form-item>
        <el-form-item label="工作日期" prop="workDate">
          <el-date-picker
            v-model="createForm.workDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="班别" prop="shiftType">
          <el-radio-group v-model="createForm.shiftType">
            <el-radio value="day">白班</el-radio>
            <el-radio value="night">晚班</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="工时" prop="workHours">
          <el-input-number
            v-model="createForm.workHours"
            :min="0"
            :max="24"
            :step="0.5"
            :precision="1"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="加班" prop="overtimeHours">
          <el-input-number
            v-model="createForm.overtimeHours"
            :min="0"
            :max="24"
            :step="0.5"
            :precision="1"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="审批状态" prop="approvalStatus">
          <el-select v-model="createForm.approvalStatus" style="width: 100%">
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmitCreate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Download, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  createEmployeeWorkHour,
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
const items = ref([])
const total = ref(0)
const workHoursSum = ref(0)
const overtimeHoursSum = ref(0)
const page = ref(1)
const pageSize = ref(10)
const departmentOptions = ref([])
const employeeOptions = ref([])
const projectOptions = ref([])
const dateRange = ref(defaultDateRange())
const viewMode = ref('detail')

const createVisible = ref(false)
const submitting = ref(false)
const createFormRef = ref(null)

const filters = reactive({
  department: '',
  employeeNo: '',
  projectName: '',
})

const createForm = reactive({
  employeeNo: '',
  employeeName: '',
  department: '',
  projectName: '',
  taskName: '',
  workDate: new Date().toISOString().slice(0, 10),
  shiftType: 'day',
  workHours: 8,
  overtimeHours: 0,
  approvalStatus: 'pending',
})

const createRules = {
  employeeNo: [{ required: true, message: '请填写工号', trigger: 'blur' }],
  employeeName: [{ required: true, message: '请填写姓名', trigger: 'blur' }],
  department: [{ required: true, message: '请填写部门', trigger: 'blur' }],
  projectName: [{ required: true, message: '请填写项目', trigger: 'blur' }],
  taskName: [{ required: true, message: '请填写任务', trigger: 'blur' }],
  workDate: [{ required: true, message: '请选择日期', trigger: 'change' }],
  workHours: [{ required: true, message: '请填写工时', trigger: 'change' }],
}

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(1)
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
    const dimension = viewMode.value === 'employee' ? 'employee' : 'detail'
    const resp = await fetchEmployeeWorkHoursReport({
      page: page.value,
      pageSize: pageSize.value,
      dateFrom: (dateRange.value && dateRange.value[0]) || '',
      dateTo: (dateRange.value && dateRange.value[1]) || '',
      department: filters.department || undefined,
      employeeNo: filters.employeeNo || undefined,
      projectName: filters.projectName || undefined,
      dimension,
    })
    items.value = resp.items || []
    total.value = resp.total || 0
    workHoursSum.value = resp.work_hours_sum ?? 0
    overtimeHoursSum.value = resp.overtime_hours_sum ?? 0
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

async function handleExport() {
  try {
    const dimension = viewMode.value === 'employee' ? 'employee' : 'detail'
    const blob = await exportEmployeeWorkHoursReport({
      dateFrom: (dateRange.value && dateRange.value[0]) || '',
      dateTo: (dateRange.value && dateRange.value[1]) || '',
      department: filters.department || undefined,
      employeeNo: filters.employeeNo || undefined,
      projectName: filters.projectName || undefined,
      dimension,
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `员工工时报表_${new Date().toISOString().slice(0, 10)}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    ElMessage.error(err.message || '导出失败')
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
  dateRange.value = defaultDateRange()
  viewMode.value = 'detail'
  page.value = 1
  loadReport()
}

function openCreate() {
  createVisible.value = true
}

function resetCreateForm() {
  createForm.employeeNo = ''
  createForm.employeeName = ''
  createForm.department = ''
  createForm.projectName = ''
  createForm.taskName = ''
  createForm.workDate = new Date().toISOString().slice(0, 10)
  createForm.shiftType = 'day'
  createForm.workHours = 8
  createForm.overtimeHours = 0
  createForm.approvalStatus = 'pending'
  createFormRef.value?.clearValidate()
}

function onCreateEmployeeChange(employeeNo) {
  const emp = employeeOptions.value.find((e) => e.employee_no === employeeNo)
  if (emp) {
    createForm.employeeName = emp.employee_name
    if (emp.department) {
      createForm.department = emp.department
    }
  }
}

async function handleSubmitCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await createEmployeeWorkHour({
      employee_no: createForm.employeeNo,
      employee_name: createForm.employeeName,
      department: createForm.department,
      project_name: createForm.projectName,
      task_name: createForm.taskName,
      work_date: createForm.workDate,
      shift_type: createForm.shiftType,
      work_hours: createForm.workHours,
      overtime_hours: createForm.overtimeHours,
      approval_status: createForm.approvalStatus,
    })
    ElMessage.success('工时记录已保存')
    createVisible.value = false
    await loadFilters()
    page.value = 1
    await loadReport()
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    submitting.value = false
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
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
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
</style>
