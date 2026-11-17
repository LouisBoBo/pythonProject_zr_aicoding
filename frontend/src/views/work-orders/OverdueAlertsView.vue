<template>
  <div class="overdue-alerts-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="产线">
          <el-input
            v-model="filters.productionLine"
            placeholder="产线"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="工单号 / 产品名"
            clearable
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
        <span class="table-title">工单逾期预警</span>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="order_no" label="工单号" min-width="130" />
        <el-table-column prop="product_name" label="产品" min-width="120" />
        <el-table-column prop="production_line" label="产线" min-width="90">
          <template #default="{ row }">{{ row.production_line || '-' }}</template>
        </el-table-column>
        <el-table-column prop="plan_quantity" label="计划数" width="90" align="center" />
        <el-table-column prop="actual_quantity" label="实际数" width="90" align="center" />
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="priorityTagType(row.priority)" size="small">{{ priorityLabel(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="assignee" label="负责人" min-width="80">
          <template #default="{ row }">{{ row.assignee || '-' }}</template>
        </el-table-column>
        <el-table-column prop="end_date" label="计划结束" width="110" />
        <el-table-column prop="overdue_days" label="逾期天数" width="100" align="center">
          <template #default="{ row }">
            <span class="overdue-days">{{ row.overdue_days }} 天</span>
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
          @size-change="loadList"
          @current-change="loadList"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchWorkOrderAlerts } from '../../api/workOrderAlerts'

const router = useRouter()

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(true)

const filters = reactive({
  productionLine: '',
  keyword: '',
})

const priorityLabels = {
  low: '低',
  normal: '普通',
  high: '高',
  urgent: '紧急',
}

const statusLabels = {
  pending: '待开工',
  in_progress: '进行中',
  completed: '已完成',
  closed: '已关闭',
  cancelled: '已取消',
}

function priorityLabel(priority) {
  return priorityLabels[priority] || priority
}

function statusLabel(status) {
  return statusLabels[status] || status
}

function statusTagType(status) {
  const map = {
    pending: 'info',
    in_progress: '',
    completed: 'success',
    closed: 'success',
    cancelled: 'danger',
  }
  return map[status] || 'info'
}

function priorityTagType(priority) {
  const map = {
    low: 'info',
    normal: '',
    high: 'warning',
    urgent: 'danger',
  }
  return map[priority] || 'info'
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.productionLine = ''
  filters.keyword = ''
  page.value = 1
  loadList()
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchWorkOrderAlerts({
      page: page.value,
      size: pageSize.value,
      productionLine: filters.productionLine || undefined,
      keyword: filters.keyword || undefined,
    })
    items.value = data.items
    total.value = data.total
  } catch (err) {
    if (err.message === '未登录') {
      router.push('/login')
      return
    }
    ElMessage.error(err.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.overdue-alerts-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-card,
.table-card {
  border-radius: 12px;
}

.search-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.table-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.overdue-days {
  color: #f56c6c;
  font-weight: 600;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
