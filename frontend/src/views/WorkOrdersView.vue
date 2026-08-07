<template>
  <div class="work-orders-page">
    <div class="page-toolbar">
      <button class="create-btn" @click="openCreateModal">新建工单</button>
    </div>

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

    <Teleport to="body">
      <div
        v-if="showCreateModal"
        class="modal-overlay"
        @click.self="closeCreateModal"
      >
        <div
          class="modal-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-modal-title"
        >
          <header class="modal-header">
            <div>
              <h2 id="create-modal-title">新建工单</h2>
              <p class="modal-subtitle">填写工单信息并提交</p>
            </div>
            <button type="button" class="modal-close" aria-label="关闭" @click="closeCreateModal">
              ×
            </button>
          </header>

          <form class="create-form" @submit.prevent="handleCreateSubmit">
            <div class="form-group">
              <label for="order-no">工单号</label>
              <input
                id="order-no"
                v-model="createForm.order_no"
                type="text"
                placeholder="请输入工单号"
                maxlength="50"
                required
              />
            </div>

            <div class="form-group">
              <label for="product-name">产品名</label>
              <input
                id="product-name"
                v-model="createForm.product_name"
                type="text"
                placeholder="请输入产品名"
                maxlength="100"
                required
              />
            </div>

            <div class="form-group">
              <label for="product-code">产品编码</label>
              <input
                id="product-code"
                v-model="createForm.product_code"
                type="text"
                placeholder="请输入产品编码"
                maxlength="50"
              />
            </div>

            <div class="form-group">
              <label for="production-line">生产线</label>
              <input
                id="production-line"
                v-model="createForm.production_line"
                type="text"
                placeholder="请输入生产线"
                maxlength="50"
              />
            </div>

            <div class="form-group">
              <label for="plan-quantity">计划数量</label>
              <input
                id="plan-quantity"
                v-model.number="createForm.plan_quantity"
                type="number"
                min="1"
                placeholder="请输入计划数量"
                required
              />
            </div>

            <div class="form-group">
              <label for="priority">优先级</label>
              <select id="priority" v-model="createForm.priority">
                <option value="low">低</option>
                <option value="normal">普通</option>
                <option value="high">高</option>
                <option value="urgent">紧急</option>
              </select>
            </div>

            <div class="form-group">
              <label for="assignee">负责人</label>
              <input
                id="assignee"
                v-model="createForm.assignee"
                type="text"
                placeholder="请输入负责人"
                maxlength="50"
              />
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="start-date">开始日期</label>
                <input id="start-date" v-model="createForm.start_date" type="date" />
              </div>
              <div class="form-group">
                <label for="end-date">结束日期</label>
                <input id="end-date" v-model="createForm.end_date" type="date" />
              </div>
            </div>

            <div class="form-group">
              <label for="remark">备注</label>
              <textarea
                id="remark"
                v-model="createForm.remark"
                placeholder="请输入备注"
                maxlength="500"
                rows="3"
              />
            </div>

            <p v-if="createError" class="create-error">{{ createError }}</p>

            <div class="form-actions">
              <button type="button" class="cancel-btn" @click="closeCreateModal">取消</button>
              <button type="submit" class="submit-btn" :disabled="createLoading">
                {{ createLoading ? '提交中...' : '提交' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createWorkOrder, fetchWorkOrders } from '../api/workOrders'

const router = useRouter()
const route = useRoute()

const workOrders = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(true)
const error = ref('')
const statusFilter = ref('')
const priorityFilter = ref('')

const showCreateModal = ref(false)
const createLoading = ref(false)
const createError = ref('')

const defaultCreateForm = () => ({
  order_no: '',
  product_name: '',
  product_code: '',
  production_line: '',
  plan_quantity: null,
  priority: 'normal',
  assignee: '',
  start_date: '',
  end_date: '',
  remark: '',
})

const createForm = ref(defaultCreateForm())

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

function resetCreateForm() {
  createForm.value = defaultCreateForm()
  createError.value = ''
}

function openCreateModal() {
  resetCreateForm()
  showCreateModal.value = true
}

function closeCreateModal() {
  showCreateModal.value = false
  createLoading.value = false
  resetCreateForm()
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

async function handleCreateSubmit() {
  createError.value = ''
  createLoading.value = true
  try {
    const payload = {
      order_no: createForm.value.order_no.trim(),
      product_name: createForm.value.product_name.trim(),
      plan_quantity: createForm.value.plan_quantity,
      priority: createForm.value.priority,
    }
    if (createForm.value.product_code.trim()) {
      payload.product_code = createForm.value.product_code.trim()
    }
    if (createForm.value.production_line.trim()) {
      payload.production_line = createForm.value.production_line.trim()
    }
    if (createForm.value.assignee.trim()) {
      payload.assignee = createForm.value.assignee.trim()
    }
    if (createForm.value.start_date) {
      payload.start_date = createForm.value.start_date
    }
    if (createForm.value.end_date) {
      payload.end_date = createForm.value.end_date
    }
    if (createForm.value.remark.trim()) {
      payload.remark = createForm.value.remark.trim()
    }
    await createWorkOrder(payload)
    closeCreateModal()
    page.value = 1
    await loadWorkOrders()
  } catch (err) {
    createError.value = err.message || '提交失败，请重试'
  } finally {
    createLoading.value = false
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
  if (route.query.create === '1' || route.query.create === 'true') {
    openCreateModal()
    router.replace({ path: '/work-orders' })
  }
})
</script>

<style scoped>
.work-orders-page {
  display: flex;
  flex-direction: column;
}

.page-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.create-btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
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
  max-width: 1280px;
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

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(26, 26, 46, 0.45);
}

.modal-dialog {
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 24px 24px 0;
}

.modal-header h2 {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
}

.modal-subtitle {
  margin-top: 4px;
  font-size: 14px;
  color: #666;
}

.modal-close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: #f5f5f5;
  color: #666;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
}

.modal-close:hover {
  background: #ececec;
  color: #333;
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px 24px 24px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 14px;
  font-weight: 500;
  color: #444;
}

.form-group input,
.form-group select,
.form-group textarea {
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 15px;
  transition: border-color 0.2s;
  background: #fff;
  font-family: inherit;
}

.form-group textarea {
  resize: vertical;
  min-height: 72px;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15);
}

.create-error {
  color: #e53e3e;
  font-size: 14px;
  text-align: center;
}

.form-actions {
  display: flex;
  gap: 12px;
}

.cancel-btn,
.submit-btn {
  flex: 1;
  padding: 12px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.cancel-btn {
  background: #fff;
  border: 1px solid #ddd;
  color: #444;
}

.cancel-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.submit-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border: none;
}

.submit-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 560px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
