<template>
  <div class="work-hours-list-page">
    <el-card shadow="never" class="search-card">
      <div class="page-heading">
        <h2 class="page-title">员工工时列表</h2>
        <p class="page-desc">查询员工工时填报明细与审批状态</p>
      </div>
      <el-form :model="filters" inline class="search-form" @submit.prevent="handleSearch">
        <el-form-item label="工号">
          <el-input
            v-model="filters.employeeNo"
            placeholder="工号"
            clearable
            style="width: 140px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input
            v-model="filters.employeeName"
            placeholder="姓名"
            clearable
            style="width: 120px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="部门">
          <el-input
            v-model="filters.department"
            placeholder="部门"
            clearable
            style="width: 140px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始"
            end-placeholder="结束"
            value-format="YYYY-MM-DD"
            clearable
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item label="审批">
          <el-select
            v-model="filters.approvalStatus"
            placeholder="全部"
            clearable
            style="width: 110px"
          >
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <span class="table-title">工时明细</span>
        <span v-if="total > 0" class="table-summary">共 {{ total }} 条</span>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="employee_no" label="工号" width="100" />
        <el-table-column prop="employee_name" label="员工" width="90" />
        <el-table-column prop="department" label="部门" min-width="100" />
        <el-table-column prop="work_date" label="报工日期" width="115" />
        <el-table-column prop="project_name" label="项目" min-width="120" show-overflow-tooltip />
        <el-table-column prop="task_name" label="任务" min-width="100" show-overflow-tooltip />
        <el-table-column prop="work_hours" label="工时(h)" width="90" align="right" />
        <el-table-column prop="overtime_hours" label="加班(h)" width="90" align="right" />
        <el-table-column prop="approval_status" label="审批" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="approvalTagType(row.approval_status)" size="small" effect="light">
              {{ row.approval_status }}
            </el-tag>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无工时记录" />
        </template>
      </el-table>

      <div class="pagination-wrap">
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
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchEmployeeWorkHoursList } from '../../api/employeeWorkHoursList'

const filters = reactive({
  employeeNo: '',
  employeeName: '',
  department: '',
  approvalStatus: '',
})

const dateRange = ref(null)
const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

function approvalTagType(label) {
  if (label === '已通过') return 'success'
  if (label === '待审批') return 'warning'
  if (label === '已驳回') return 'danger'
  return 'info'
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchEmployeeWorkHoursList({
      page: page.value,
      pageSize: pageSize.value,
      employeeNo: filters.employeeNo || undefined,
      employeeName: filters.employeeName || undefined,
      department: filters.department || undefined,
      dateFrom: dateRange.value?.[0] || undefined,
      dateTo: dateRange.value?.[1] || undefined,
      approvalStatus: filters.approvalStatus || undefined,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    items.value = []
    total.value = 0
    ElMessage.error(err.message || '加载员工工时列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.employeeNo = ''
  filters.employeeName = ''
  filters.department = ''
  filters.approvalStatus = ''
  dateRange.value = null
  page.value = 1
  loadList()
}

onMounted(loadList)
</script>

<style scoped>
.work-hours-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 100%;
}

.search-card,
.table-card {
  border-radius: 8px;
  border: 1px solid #e8ecf1;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.page-heading {
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.page-title {
  margin: 0 0 4px;
  font-size: 17px;
  font-weight: 600;
  color: #303133;
}

.page-desc {
  margin: 0;
  font-size: 13px;
  color: #909399;
}

.search-form {
  margin-bottom: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  align-items: center;
}

.search-form :deep(.el-form-item) {
  margin-bottom: 8px;
  margin-right: 12px;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.table-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.table-summary {
  font-size: 13px;
  color: #606266;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
