<template>
  <div class="employee-page">
    <el-card shadow="never" class="search-card">
      <div class="page-heading">
        <h2 class="page-title">员工列表</h2>
        <p class="page-desc">查看部门、员工资料与月工资</p>
      </div>
      <el-form :model="filters" inline class="search-form" @submit.prevent="handleSearch">
        <el-form-item label="工号">
          <el-input
            v-model="filters.employeeNo"
            placeholder="请输入工号"
            clearable
            style="width: 160px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input
            v-model="filters.employeeName"
            placeholder="请输入姓名"
            clearable
            style="width: 160px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="部门">
          <el-input
            v-model="filters.departmentName"
            placeholder="请输入部门名称"
            clearable
            style="width: 180px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <span class="table-title">员工</span>
        <span v-if="total > 0" class="table-summary">共 {{ total }} 人</span>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="department_code" label="部门编码" min-width="110" />
        <el-table-column prop="department_name" label="部门名称" min-width="110" />
        <el-table-column prop="employee_no" label="工号" min-width="100" />
        <el-table-column prop="employee_name" label="姓名" width="90" />
        <el-table-column prop="gender" label="性别" width="70" align="center" />
        <el-table-column prop="position" label="岗位" min-width="120" />
        <el-table-column prop="phone" label="手机" min-width="130">
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>
        <el-table-column prop="hire_date" label="入职日期" width="120" />
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small" effect="light">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="salary" label="工资" width="120" align="right">
          <template #default="{ row }">{{ formatSalary(row.salary) }}</template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无员工数据" />
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
import { fetchEmployeeList } from '../../api/employees'

const filters = reactive({
  employeeNo: '',
  employeeName: '',
  departmentName: '',
})

const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

function formatSalary(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return `¥${num.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function statusLabel(status) {
  const map = {
    active: '在职',
    inactive: '离职',
    leave: '请假',
    probation: '试用',
  }
  return map[status] || status || '-'
}

function statusTagType(status) {
  const label = statusLabel(status)
  if (label === '在职' || status === 'active') return 'success'
  if (label === '离职' || status === 'inactive') return 'info'
  if (label === '请假' || status === 'leave') return 'warning'
  if (label === '试用' || status === 'probation') return ''
  return 'info'
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchEmployeeList({
      page: page.value,
      pageSize: pageSize.value,
      employeeNo: filters.employeeNo || undefined,
      employeeName: filters.employeeName || undefined,
      departmentName: filters.departmentName || undefined,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    items.value = []
    total.value = 0
    ElMessage.error(err.message || '加载员工列表失败')
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
  filters.departmentName = ''
  page.value = 1
  loadList()
}

onMounted(loadList)
</script>

<style scoped>
.employee-page {
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
