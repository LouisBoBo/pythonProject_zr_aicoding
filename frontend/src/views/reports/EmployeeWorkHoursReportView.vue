<template>
  <div class="work-hours-page">
    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <span class="table-title">员工工时报表</span>
          <el-tag size="small" type="info">明细列表</el-tag>
        </div>
        <div class="toolbar-right">
          <span class="sum-text">工时合计 {{ formatHours(workHoursSum) }}</span>
          <span class="sum-text">加班合计 {{ formatHours(overtimeHoursSum) }}</span>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="employee_name" label="员工" min-width="100" />
        <el-table-column prop="department" label="部门" min-width="120" />
        <el-table-column prop="project_name" label="项目" min-width="120">
          <template #default="{ row }">{{ row.project_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="task_name" label="任务" min-width="120">
          <template #default="{ row }">{{ row.task_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="work_date" label="日期" width="120">
          <template #default="{ row }">{{ row.work_date || '—' }}</template>
        </el-table-column>
        <el-table-column prop="shift_type" label="班别" width="80">
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
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchEmployeeWorkHoursReport } from '../../api/reports/employeeWorkHours.js'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const workHoursSum = ref(0)
const overtimeHoursSum = ref(0)

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(1)
}

async function loadReport() {
  loading.value = true
  try {
    const resp = await fetchEmployeeWorkHoursReport({
      page: page.value,
      pageSize: pageSize.value,
      dimension: 'detail',
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

onMounted(() => {
  loadReport()
})
</script>

<style scoped>
.work-hours-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

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
</style>
