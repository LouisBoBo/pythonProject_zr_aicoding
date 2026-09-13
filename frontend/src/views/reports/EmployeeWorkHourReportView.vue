<template>
  <div class="work-hour-report">
    <header class="work-hour-header">
      <div class="work-hour-header-main">
        <h1 class="work-hour-title">员工工时报表</h1>
        <p class="work-hour-subtitle">报表中心 · MES 报工记录 · 按员工汇总工时 · Excel 导出</p>
      </div>
      <div class="work-hour-header-meta">
        <span class="meta-label">当前筛选</span>
        <el-tag size="small" effect="plain" type="success">{{ filterSummary }}</el-tag>
        <span class="meta-count">汇总共 {{ total }} 人</span>
      </div>
    </header>

    <section class="work-hour-filter-bar">
      <el-form :model="filters" inline class="filter-form">
        <el-form-item label="日期区间">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始"
            end-placeholder="结束"
            value-format="YYYY-MM-DD"
            clearable
            style="width: 260px"
          />
        </el-form-item>
        <el-form-item label="部门">
          <el-select
            v-model="filters.department"
            placeholder="全部部门"
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
            placeholder="全部员工"
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
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
          <el-button :icon="Download" :loading="exporting" @click="handleExport">导出 Excel</el-button>
        </el-form-item>
      </el-form>
    </section>

    <div class="metric-cards">
      <el-card v-for="card in metricCards" :key="card.key" shadow="never" class="metric-card">
        <div class="metric-label">{{ card.label }}</div>
        <div class="metric-value" :class="{ highlight: card.highlight }">
          {{ card.value }}<span v-if="card.unit" class="metric-unit">{{ card.unit }}</span>
        </div>
      </el-card>
    </div>

    <section class="work-hour-table-section">
      <div class="table-toolbar">
        <span class="table-title">员工工时汇总</span>
        <el-tag size="small" type="info">按员工维度汇总 MES 报工记录</el-tag>
      </div>

      <el-table
        v-loading="loading"
        :data="items"
        stripe
        border
        class="work-hour-table"
        empty-text="暂无报工汇总数据"
      >
        <el-table-column prop="employee_no" label="工号" width="100" fixed="left" />
        <el-table-column prop="employee_name" label="员工姓名" width="110" fixed="left" />
        <el-table-column prop="department" label="所属部门" min-width="120" show-overflow-tooltip />
        <el-table-column label="工时数" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
        </el-table-column>
        <el-table-column label="加班工时" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.overtime_hours) }}</template>
        </el-table-column>
        <el-table-column prop="record_count" label="报工条数" width="100" align="right">
          <template #default="{ row }">{{ row.record_count ?? '—' }}</template>
        </el-table-column>
      </el-table>

      <div class="work-hour-pagination">
        <span class="page-info">第 {{ page }} / {{ totalPages }} 页，本页 {{ items.length }} 条</span>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="loadList"
          @current-change="loadList"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  exportEmployeeWorkHourReport,
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
const exporting = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const dateRange = ref(defaultDateRange())
const departmentOptions = ref([])
const employeeOptions = ref([])
const workHoursSum = ref(0)
const overtimeHoursSum = ref(0)

const filters = reactive({
  department: '',
  employeeNo: '',
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const metricCards = computed(() => [
  { key: 'work', label: '工时合计', value: formatHours(workHoursSum.value), highlight: true },
  { key: 'overtime', label: '加班工时合计', value: formatHours(overtimeHoursSum.value) },
  { key: 'count', label: '汇总人数', value: total.value },
])

const filterSummary = computed(() => {
  const parts = []
  if (dateRange.value?.length === 2) parts.push(`日期 ${dateRange.value[0]} ~ ${dateRange.value[1]}`)
  if (filters.department) parts.push(`部门「${filters.department}」`)
  if (filters.employeeNo) {
    const emp = employeeOptions.value.find((e) => e.employee_no === filters.employeeNo)
    parts.push(`员工「${emp ? emp.employee_name : filters.employeeNo}」`)
  }
  return parts.length ? parts.join(' · ') : '近 30 日 · 全部员工'
})

function formatHours(value) {
  const num = Number(value)
  if (Number.isNaN(num)) return '—'
  return num.toFixed(2)
}

function buildQueryParams() {
  return {
    page: page.value,
    pageSize: pageSize.value,
    dateFrom: dateRange.value?.[0] || undefined,
    dateTo: dateRange.value?.[1] || undefined,
    department: filters.department || undefined,
    employeeNo: filters.employeeNo || undefined,
    dimension: 'employee',
  }
}

async function loadFilters() {
  try {
    const resp = await fetchEmployeeWorkHourFilters()
    departmentOptions.value = resp.departments || []
    employeeOptions.value = resp.employees || []
  } catch (err) {
    ElMessage.warning(err.message || '加载筛选选项失败')
    departmentOptions.value = []
    employeeOptions.value = []
  }
}

async function loadList() {
  loading.value = true
  try {
    const resp = await fetchEmployeeWorkHourReport(buildQueryParams())
    items.value = resp.items || []
    total.value = resp.total ?? 0
    workHoursSum.value = resp.work_hours_sum ?? 0
    overtimeHoursSum.value = resp.overtime_hours_sum ?? 0
  } catch (err) {
    ElMessage.error(err.message || '加载员工工时报表失败')
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
  loadList()
}

function handleReset() {
  filters.department = ''
  filters.employeeNo = ''
  dateRange.value = defaultDateRange()
  page.value = 1
  loadList()
}

async function handleExport() {
  exporting.value = true
  try {
    const { page: _p, pageSize: _s, ...exportParams } = buildQueryParams()
    const blob = await exportEmployeeWorkHourReport(exportParams)
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
  loadList()
})
</script>

<style scoped>
.work-hour-report {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 120px);
  background: var(--el-bg-color);
}

.work-hour-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 20px 24px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.work-hour-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.work-hour-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.work-hour-header-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.meta-label {
  color: var(--el-text-color-placeholder);
}

.meta-count {
  font-weight: 500;
  color: var(--el-text-color-regular);
}

.work-hour-filter-bar {
  padding: 16px 24px 8px;
  background: var(--el-fill-color-blank);
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 0;
}

.metric-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  padding: 12px 24px;
}

.metric-card {
  border-radius: 8px;
}

.metric-card :deep(.el-card__body) {
  padding: 14px 16px;
}

.metric-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}

.metric-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.metric-value.highlight {
  color: var(--el-color-primary);
}

.metric-unit {
  margin-left: 2px;
  font-size: 14px;
  font-weight: 500;
}

.work-hour-table-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0 24px 24px;
}

.table-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.table-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.work-hour-table {
  flex: 1;
}

.work-hour-pagination {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
}

.page-info {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>
