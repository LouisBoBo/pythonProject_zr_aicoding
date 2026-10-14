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
        <el-form-item label="项目">
          <el-select
            v-model="filters.projectName"
            placeholder="全部"
            clearable
            filterable
            style="width: 160px"
          >
            <el-option
              v-for="name in projectOptions"
              :key="name"
              :label="name"
              :value="name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="班别">
          <el-select
            v-model="filters.shiftType"
            placeholder="全部"
            clearable
            style="width: 120px"
          >
            <el-option label="白班" value="day" />
            <el-option label="晚班" value="night" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="viewMode === 'detail'" label="审批">
          <el-select
            v-model="filters.approvalStatus"
            placeholder="全部"
            clearable
            style="width: 120px"
          >
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item label="视图">
          <el-radio-group v-model="viewMode" @change="handleViewModeChange">
            <el-radio-button value="detail">明细</el-radio-button>
            <el-radio-button value="employee">按员工</el-radio-button>
            <el-radio-button value="project">按项目</el-radio-button>
            <el-radio-button value="department">按部门</el-radio-button>
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
          <el-tag size="small" type="info">{{ viewLabel }}</el-tag>
          <el-tag size="small" type="success">
            已通过合计 {{ formatHours(workHoursSum) }} h
          </el-tag>
        </div>
        <div class="toolbar-right">
          <template v-if="viewMode === 'detail' && canApprove">
            <el-button
              type="success"
              :disabled="!selectedPendingIds.length"
              :loading="approving"
              @click="handleBatch('approved')"
            >
              通过
            </el-button>
            <el-button
              type="danger"
              plain
              :disabled="!selectedPendingIds.length"
              :loading="approving"
              @click="handleBatch('rejected')"
            >
              驳回
            </el-button>
          </template>
          <el-button :loading="exporting" @click="handleExport">导出</el-button>
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
          v-if="viewMode === 'detail' && canApprove"
          type="selection"
          width="48"
          :selectable="rowSelectable"
        />
        <el-table-column
          v-if="viewMode === 'detail' || viewMode === 'employee'"
          prop="employee_name"
          label="员工"
          min-width="110"
        />
        <el-table-column
          v-if="viewMode === 'detail' || viewMode === 'employee'"
          prop="employee_no"
          label="工号"
          width="110"
        >
          <template #default="{ row }">{{ row.employee_no || '—' }}</template>
        </el-table-column>
        <el-table-column
          v-if="viewMode !== 'project'"
          prop="department"
          label="部门"
          min-width="120"
        />
        <el-table-column
          v-if="viewMode === 'detail' || viewMode === 'project'"
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
        <el-table-column
          v-if="viewMode === 'detail'"
          prop="work_date"
          label="日期"
          width="120"
        >
          <template #default="{ row }">{{ row.work_date || '—' }}</template>
        </el-table-column>
        <el-table-column
          v-if="viewMode === 'detail'"
          prop="shift_type"
          label="班别"
          width="80"
          align="center"
        >
          <template #default="{ row }">{{ row.shift_type || '—' }}</template>
        </el-table-column>
        <el-table-column prop="work_hours" label="工时" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
        </el-table-column>
        <el-table-column
          v-if="viewMode !== 'detail'"
          prop="record_count"
          label="条数"
          width="80"
          align="center"
        />
        <el-table-column
          v-if="viewMode === 'detail'"
          prop="approval_status"
          label="审批"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              effect="light"
              :type="approvalTagType(row.approval_status_code)"
            >
              {{ row.approval_status || '—' }}
            </el-tag>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePermissions } from '../../composables/usePermissions'
import {
  batchApproveEmployeeWorkHours,
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

const { can } = usePermissions()
const canApprove = computed(() => can('work_hours.approve'))

const loading = ref(false)
const exporting = ref(false)
const approving = ref(false)
const items = ref([])
const total = ref(0)
const workHoursSum = ref(0)
const page = ref(1)
const pageSize = ref(10)
const departmentOptions = ref([])
const projectOptions = ref([])
const dateRange = ref(defaultDateRange())
const viewMode = ref('detail')
const selectedRows = ref([])

const filters = reactive({
  department: '',
  projectName: '',
  shiftType: '',
  approvalStatus: '',
})

const viewLabel = computed(() => {
  const map = {
    detail: '明细列表',
    employee: '按员工汇总（默认已通过）',
    project: '按项目汇总（默认已通过）',
    department: '按部门汇总（默认已通过）',
  }
  return map[viewMode.value] || '报表'
})

const selectedPendingIds = computed(() =>
  selectedRows.value
    .filter((r) => r.approval_status_code === 'pending' && r.id != null)
    .map((r) => r.id),
)

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(1)
}

function approvalTagType(code) {
  if (code === 'approved') return 'success'
  if (code === 'rejected') return 'danger'
  if (code === 'pending') return 'warning'
  return 'info'
}

function rowSelectable(row) {
  return row.approval_status_code === 'pending'
}

function handleSelectionChange(rows) {
  selectedRows.value = rows || []
}

function handleViewModeChange() {
  page.value = 1
  selectedRows.value = []
  if (viewMode.value !== 'detail') {
    filters.approvalStatus = ''
  }
  loadReport()
}

function buildQuery(extra = {}) {
  return {
    page: page.value,
    pageSize: pageSize.value,
    dateFrom: (dateRange.value && dateRange.value[0]) || '',
    dateTo: (dateRange.value && dateRange.value[1]) || '',
    department: filters.department || undefined,
    projectName: filters.projectName || undefined,
    shiftType: filters.shiftType || undefined,
    approvalStatus:
      viewMode.value === 'detail' && filters.approvalStatus
        ? filters.approvalStatus
        : undefined,
    dimension: viewMode.value,
    ...extra,
  }
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
    const resp = await fetchEmployeeWorkHoursReport(buildQuery())
    items.value = resp.items || []
    total.value = resp.total || 0
    workHoursSum.value = resp.work_hours_sum ?? 0
    selectedRows.value = []
  } catch (err) {
    items.value = []
    total.value = 0
    workHoursSum.value = 0
    ElMessage.error(err.message || '加载员工工时报表失败')
  } finally {
    loading.value = false
  }
}

async function handleBatch(approvalStatus) {
  const ids = selectedPendingIds.value
  if (!ids.length) return
  const label = approvalStatus === 'approved' ? '通过' : '驳回'
  try {
    await ElMessageBox.confirm(
      `确认${label}选中的 ${ids.length} 条待审批工时？`,
      '批量审批',
      { type: approvalStatus === 'approved' ? 'success' : 'warning' },
    )
  } catch {
    return
  }
  approving.value = true
  try {
    const resp = await batchApproveEmployeeWorkHours({ ids, approvalStatus })
    ElMessage.success(`已更新 ${resp.updated ?? 0} 条`)
    await loadReport()
  } catch (err) {
    ElMessage.error(err.message || '审批失败')
  } finally {
    approving.value = false
  }
}

async function handleExport() {
  exporting.value = true
  try {
    const blob = await exportEmployeeWorkHoursReport({
      ...buildQuery(),
      // 导出默认已通过；明细若选了审批状态则跟随
      approvalStatus:
        viewMode.value === 'detail' && filters.approvalStatus
          ? filters.approvalStatus
          : undefined,
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `employee-work-hours-${viewMode.value}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    ElMessage.error(err.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadReport()
}

function handleReset() {
  filters.department = ''
  filters.projectName = ''
  filters.shiftType = ''
  filters.approvalStatus = ''
  dateRange.value = defaultDateRange()
  viewMode.value = 'detail'
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

.search-form {
  margin-bottom: 0;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
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

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
