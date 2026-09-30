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
          prop="shift_type"
          label="班别"
          width="90"
          align="center"
        >
          <template #default="{ row }">{{ row.shift_type || '—' }}</template>
        </el-table-column>
        <el-table-column prop="work_hours" label="工时" width="120" align="right">
          <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
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
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const departmentOptions = ref([])
const dateRange = ref(defaultDateRange())
const viewMode = ref('detail')

const filters = reactive({
  department: '',
  shiftType: '',
})

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
  } catch {
    departmentOptions.value = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const resp = await fetchEmployeeWorkHoursReport({
      page: page.value,
      pageSize: pageSize.value,
      dateFrom: (dateRange.value && dateRange.value[0]) || '',
      dateTo: (dateRange.value && dateRange.value[1]) || '',
      department: filters.department || undefined,
      shiftType: filters.shiftType || undefined,
      dimension: viewMode.value === 'employee' ? 'employee' : 'detail',
    })
    items.value = resp.items || []
    total.value = resp.total || 0
  } catch (err) {
    items.value = []
    total.value = 0
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
  filters.shiftType = ''
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
  margin-bottom: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
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
