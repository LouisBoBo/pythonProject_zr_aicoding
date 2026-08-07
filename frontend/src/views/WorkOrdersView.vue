<template>
  <div class="work-orders-page">
    <header class="header">
      <button class="back-btn" @click="router.push('/home')">← 返回首页</button>
      <h1>工单管理</h1>
      <button class="create-btn" @click="openCreateModal">新建工单</button>
    </header>

    <main class="content">
      <div class="table-card">
        <div v-if="loading" class="loading-hint">加载中...</div>
        <div v-else-if="error" class="error-hint">{{ error }}</div>
        <template v-else>
          <table class="data-table">
            <thead>
              <tr>
                <th>工单号</th>
                <th>产品名</th>
                <th>产品编码</th>
                <th>生产线</th>
                <th>计划数量</th>
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
                <td>{{ order.product_code }}</td>
                <td>{{ order.production_line }}</td>
                <td>{{ order.plan_quantity }}</td>
                <td>
                  <span class="priority-tag" :class="'priority-' + order.priority">
                    {{ priorityLabel(order.priority) }}
                  </span>
                </td>
                <td>{{ order.assignee }}</td>
                <td>{{ order.start_date }}</td>
                <td>{{ order.end_date }}</td>
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

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h2>新建工单</h2>
          <button class="close-btn" @click="closeModal">×</button>
        </div>
        <form class="modal-form" @submit.prevent="handleSubmit">
          <div class="form-row">
            <label>产品名</label>
            <input v-model="form.product_name" required maxlength="100" placeholder="请输入产品名" />
          </div>
          <div class="form-row">
            <label>产品编码</label>
            <input v-model="form.product_code" required maxlength="50" placeholder="请输入产品编码" />
          </div>
          <div class="form-row">
            <label>生产线</label>
            <input v-model="form.production_line" required maxlength="50" placeholder="请输入生产线" />
          </div>
          <div class="form-row">
            <label>计划数量</label>
            <input v-model.number="form.plan_quantity" type="number" required min="1" placeholder="请输入计划数量" />
          </div>
          <div class="form-row">
            <label>优先级</label>
            <select v-model="form.priority" required>
              <option value="low">低</option>
              <option value="normal">普通</option>
              <option value="high">高</option>
              <option value="urgent">紧急</option>
            </select>
          </div>
          <div class="form-row">
            <label>负责人</label>
            <input v-model="form.assignee" required maxlength="50" placeholder="请输入负责人" />
          </div>
          <div class="form-row">
            <label>开始日期</label>
            <input v-model="form.start_date" type="date" required />
          </div>
          <div class="form-row">
            <label>结束日期</label>
            <input v-model="form.end_date" type="date" required />
          </div>
          <p v-if="submitError" class="submit-error">{{ submitError }}</p>
          <div class="form-actions">
            <button type="button" class="cancel-btn" @click="closeModal">取消</button>
            <button type="submit" class="submit-btn" :disabled="submitting">
              {{ submitting ? '提交中...' : '提交' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createWorkOrder, fetchWorkOrders } from '../api/workOrders'

const router = useRouter()

const workOrders = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(true)
const error = ref('')

const showModal = ref(false)
const submitting = ref(false)
const submitError = ref('')

const emptyForm = () => ({
  product_name: '',
  product_code: '',
  production_line: '',
  plan_quantity: null,
  priority: 'normal',
  assignee: '',
  start_date: '',
  end_date: '',
})

const form = ref(emptyForm())

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const priorityLabels = {
  low: '低',
  normal: '普通',
  high: '高',
  urgent: '紧急',
}

function priorityLabel(priority) {
  return priorityLabels[priority] || priority
}

async function loadWorkOrders() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchWorkOrders(page.value, pageSize)
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

function changePage(newPage) {
  page.value = newPage
  loadWorkOrders()
}

function openCreateModal() {
  form.value = emptyForm()
  submitError.value = ''
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  submitError.value = ''
}

async function handleSubmit() {
  submitting.value = true
  submitError.value = ''
  try {
    await createWorkOrder(form.value)
    closeModal()
    page.value = 1
    await loadWorkOrders()
  } catch (err) {
    submitError.value = err.message
  } finally {
    submitting.value = false
  }
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

.priority-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
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
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #fff;
  border-radius: 12px;
  width: 480px;
  max-width: 90vw;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
}

.modal-header h2 {
  font-size: 18px;
  color: #1a1a2e;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #888;
  cursor: pointer;
  line-height: 1;
}

.modal-form {
  padding: 20px 24px 24px;
}

.form-row {
  margin-bottom: 14px;
}

.form-row label {
  display: block;
  font-size: 14px;
  color: #555;
  margin-bottom: 6px;
}

.form-row input,
.form-row select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.form-row input:focus,
.form-row select:focus {
  border-color: #667eea;
}

.submit-error {
  color: #c53030;
  font-size: 13px;
  margin-bottom: 12px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

.cancel-btn,
.submit-btn {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.cancel-btn {
  background: #fff;
  border: 1px solid #ddd;
}

.submit-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: #fff;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
