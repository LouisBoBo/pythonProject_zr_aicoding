<template>
  <div class="work-orders-page">
    <header class="header">
      <button class="back-btn" @click="router.push('/home')">← 返回首页</button>
      <h1>工单管理</h1>
      <button class="create-btn" @click="router.push('/work-orders/new')">新建工单</button>
    </header>

    <main class="content">
      <div class="table-card">
        <div class="filters">
          <div class="filter-group">
            <label for="status-filter">状态</label>
            <select id="status-filter" v-model="statusFilter" @change="applyFilters">
              <option value="">全部</option>
              <option value="pending">待处理</option>
              <option value="in_progress">进行中</option>
              <option value="completed">已完成</option>
              <option value="cancelled">已取消</option>
            </select>
          </div>
          <div class="filter-group">
            <label for="priority-filter">优先级</label>
            <select id="priority-filter" v-model="priorityFilter" @change="applyFilters">
              <option value="">全部</option>
              <option value="low">低</option>
              <option value="normal">普通</option>
              <option value="high">高</option>
              <option value="urgent">紧急</option>
            </select>
          </div>
        </div>

        <div v-if="loading" class="loading-hint">加载中...</div>
        <div v-else-if="error" class="error-hint">{{ error }}</div>
        <template v-else>
          <table class="data-table">
            <thead>
              <tr>
                <th>工单号</th>
                <th>产品名</th>
                <th>生产线</th>
                <th>计划数量</th>
                <th>状态</th>
                <th>优先级</th>
                <th>负责人</th>
                <th>开始日期</th>
                <th>结束日期</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!workOrders.length">
                <td colspan="9" class="empty-cell">暂无工单，点击「新建工单」创建</td>
              </tr>
              <tr v-for="order in workOrders" :key="order.id">
                <td>{{ order.order_no }}</td>
                <td>{{ order.product_name }}</td>
                <td>{{ order.production_line || '-' }}</td>
                <td>{{ order.plan_quantity }}</td>
                <td>
                  <span class="status-tag" :class="'status-' + order.status">
                    {{ statusLabel(order.status) }}
                  </span>
                </td>
                <td>
                  <span class="priority-tag" :class="'priority-' + order.priority">
                    {{ priorityLabel(order.priority) }}
                  </span>
                </td>
                <td>{{ order.assignee || '-' }}</td>
                <td>{{ order.start_date || '-' }}</td>
                <td>{{ order.end_date || '-' }}</td>
              </tr>
            </tbody>
          </table>

          <div class="pagination" v-if="total > 0">
            <span class="page-info">共 {{ total }} 条，第 {{ page }} / {{ totalPages }} 页</span>
            <div class="page-buttons">
              <button :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
              <button :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
            </div>
          </div>
        </template>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchWorkOrders } from '../api/workOrders'

const router = useRouter()

const workOrders = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(true)
const error = ref('')
const statusFilter = ref('')
const priorityFilter = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const priorityLabels = {
  low: '低',
  normal: '普通',
  high: '高',
  urgent: '紧急',
}

const statusLabels = {
  pending: '待处理',
  in_progress: '进行中',
  completed: '已完成',
  cancelled: '已取消',
}

function priorityLabel(priority) {
  return priorityLabels[priority] || priority
}

function statusLabel(status) {
  return statusLabels[status] || status
}

async function loadWorkOrders() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchWorkOrders({
      page: page.value,
      pageSize,
      status: statusFilter.value || undefined,
      priority: priorityFilter.value || undefined,
    })
    workOrders.value = data.items
    total.value = data.total
  } catch (err) {
    if (err.message === '未登录') {
      router.push('/login')
      return
    }
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  loadWorkOrders()
}

function changePage(newPage) {
  page.value = newPage
  loadWorkOrders()
}

onMounted(() => {
  loadWorkOrders()
})
</script>

<style scoped>
.work-orders-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 32px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.header h1 {
  flex: 1;
  font-size: 20px;
  color: #1a1a2e;
}

.back-btn,
.create-btn {
  padding: 6px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.back-btn {
  background: #fff;
  border: 1px solid #ddd;
}

.back-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.create-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: #fff;
  font-weight: 500;
}

.create-btn:hover {
  opacity: 0.9;
}

.content {
  flex: 1;
  padding: 24px 32px;
  max-width: 1280px;
  margin: 0 auto;
  width: 100%;
}

.table-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.filters {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group label {
  font-size: 14px;
  color: #555;
  white-space: nowrap;
}

.filter-group select {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  background: #fff;
  outline: none;
}

.filter-group select:focus {
  border-color: #667eea;
}

.loading-hint,
.error-hint {
  text-align: center;
  padding: 40px;
  color: #888;
}

.error-hint {
  color: #c53030;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.data-table th,
.data-table td {
  padding: 12px 10px;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}

.data-table th {
  font-weight: 600;
  color: #555;
  background: #fafafa;
}

.data-table tbody tr:hover {
  background: #fafbff;
}

.empty-cell {
  text-align: center;
  color: #aaa;
  padding: 32px !important;
}

.status-tag,
.priority-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.status-pending {
  background: #e2e8f0;
  color: #4a5568;
}

.status-in_progress {
  background: #bee3f8;
  color: #2b6cb0;
}

.status-completed {
  background: #c6f6d5;
  color: #276749;
}

.status-cancelled {
  background: #fed7d7;
  color: #c53030;
}

.priority-low {
  background: #e2e8f0;
  color: #4a5568;
}

.priority-normal {
  background: #bee3f8;
  color: #2b6cb0;
}

.priority-high {
  background: #fefcbf;
  color: #975a16;
}

.priority-urgent {
  background: #fed7d7;
  color: #c53030;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.page-info {
  font-size: 14px;
  color: #666;
}

.page-buttons {
  display: flex;
  gap: 8px;
}

.page-buttons button {
  padding: 6px 14px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
  font-size: 14px;
  cursor: pointer;
}

.page-buttons button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-buttons button:not(:disabled):hover {
  border-color: #667eea;
  color: #667eea;
}
</style>
