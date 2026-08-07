<template>
  <div class="new-work-order-page">
    <div class="form-card">
      <h1 class="title">新建工单</h1>
      <p class="subtitle">填写工单信息并提交</p>

      <form class="work-order-form" @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="order-no">工单号</label>
          <input
            id="order-no"
            v-model="form.order_no"
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
            v-model="form.product_name"
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
            v-model="form.product_code"
            type="text"
            placeholder="请输入产品编码"
            maxlength="50"
          />
        </div>

        <div class="form-group">
          <label for="production-line">生产线</label>
          <input
            id="production-line"
            v-model="form.production_line"
            type="text"
            placeholder="请输入生产线"
            maxlength="50"
          />
        </div>

        <div class="form-group">
          <label for="plan-quantity">计划数量</label>
          <input
            id="plan-quantity"
            v-model.number="form.plan_quantity"
            type="number"
            min="1"
            placeholder="请输入计划数量"
            required
          />
        </div>

        <div class="form-group">
          <label for="priority">优先级</label>
          <select id="priority" v-model="form.priority">
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
            v-model="form.assignee"
            type="text"
            placeholder="请输入负责人"
            maxlength="50"
          />
        </div>

        <div class="form-group">
          <label for="start-date">开始日期</label>
          <input id="start-date" v-model="form.start_date" type="date" />
        </div>

        <div class="form-group">
          <label for="end-date">结束日期</label>
          <input id="end-date" v-model="form.end_date" type="date" />
        </div>

        <div class="form-group">
          <label for="remark">备注</label>
          <textarea
            id="remark"
            v-model="form.remark"
            placeholder="请输入备注"
            maxlength="500"
            rows="3"
          />
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <div class="form-actions">
          <button type="button" class="cancel-btn" @click="router.push('/work-orders')">
            取消
          </button>
          <button type="submit" class="submit-btn" :disabled="loading">
            {{ loading ? '提交中...' : '提交' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { createWorkOrder } from '../api/workOrders'

const router = useRouter()

const form = ref({
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

const error = ref('')
const loading = ref(false)

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    const payload = {
      order_no: form.value.order_no.trim(),
      product_name: form.value.product_name.trim(),
      plan_quantity: form.value.plan_quantity,
      priority: form.value.priority,
    }
    if (form.value.product_code.trim()) {
      payload.product_code = form.value.product_code.trim()
    }
    if (form.value.production_line.trim()) {
      payload.production_line = form.value.production_line.trim()
    }
    if (form.value.assignee.trim()) {
      payload.assignee = form.value.assignee.trim()
    }
    if (form.value.start_date) {
      payload.start_date = form.value.start_date
    }
    if (form.value.end_date) {
      payload.end_date = form.value.end_date
    }
    if (form.value.remark.trim()) {
      payload.remark = form.value.remark.trim()
    }
    await createWorkOrder(payload)
    router.push('/work-orders')
  } catch (err) {
    error.value = err.message || '提交失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.new-work-order-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 24px;
}

.form-card {
  width: 100%;
  max-width: 480px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  max-height: 90vh;
  overflow-y: auto;
}

.title {
  font-size: 28px;
  font-weight: 700;
  text-align: center;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.subtitle {
  text-align: center;
  color: #666;
  margin-bottom: 32px;
  font-size: 14px;
}

.work-order-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
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

.error {
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
</style>
