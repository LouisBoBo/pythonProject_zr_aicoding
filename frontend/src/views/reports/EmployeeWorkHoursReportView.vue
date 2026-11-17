<template>
  <div class="employee-work-hours-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="报工日期">
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
        <el-form-item label="工号/姓名">
          <el-input
            v-model="filters.keyword"
            placeholder="关键字"
            clearable
            style="width: 160px"
            @keyup.enter="handleSearch"
          />
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
          <el-tag size="small" type="info">按员工 × 日期汇总报工工时</el-tag>
        </div>
        <div class="toolbar-right">
          <span class="sum-text">工时合计 {{ formatHours(workHoursSum) }}</span>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="employee_name" label="姓名" min-width="100" />
        <el-table-column prop="department_name" label="部门" min-width="120" />
        <el-table-column prop="work_date" label="日期" width="120" />
        <el-table-column prop="work_hours" label="工时（小时）" width="120" align="right">
          <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
        </el-table-column>
        <el-table-column prop="overtime_hours" label="加班工时（小时）" width="140" align="right">
          <template #default="{ row }">
            {{ row.overtime_hours == null ? '—' : formatHours(row.overtime_hours) }}
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
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchEmployeeWorkHoursFilters,
  fetchEmployeeWorkHoursReport,
} from '../../api/reports/employeeWorkHours.js'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const workHoursSum = ref(0)
const departmentOptions = ref([])
const dateRange = ref(null)

const filters = reactive({
  department: '',
  keyword: '',
})

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
}

async function loadDepartments() {
  try {
    const resp = await fetchEmployeeWorkHoursFilters()
    departmentOptions.value = resp.departments || []
  } catch {
    departmentOptions.value = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const [startDate, endDate] = Array.isArray(dateRange.value) ? dateRange.value : []
    const resp = await fetchEmployeeWorkHoursReport({
      page: page.value,
      pageSize: pageSize.value,
      startDate: startDate || undefined,
      endDate: endDate || undefined,
      department: filters.department || undefined,
      keyword: filters.keyword?.trim() || undefined,
    })
    items.value = resp.items || []
    total.value = resp.total || 0
    workHoursSum.value = resp.work_hours_sum || 0
  } catch (err) {
    ElMessage.error(err.message || '加载报表失败')
    items.value = []
    total.value = 0
    workHoursSum.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadReport()
}

function handleReset() {
  dateRange.value = null
  filters.department = ''
  filters.keyword = ''
  page.value = 1
  loadReport()
}

onMounted(async () => {
  await loadDepartments()
  await loadReport()
})
</script>

<style scoped>
.employee-work-hours-page {
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