<template>
  <div class="sales-order-create-page">
    <header class="page-header">
      <div class="header-main">
        <el-button link type="primary" class="back-btn" @click="goBack">← 返回列表</el-button>
        <h1 class="page-title">新建销售订单</h1>
        <p class="page-sub">填写客户、交期与计划数量；订单号可留空自动生成</p>
      </div>
    </header>

    <section class="form-section">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="90px"
        class="create-form"
        @submit.prevent
      >
        <el-form-item label="客户" prop="customer">
          <el-input v-model="form.customer" placeholder="客户名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="交期" prop="due_date">
          <el-date-picker
            v-model="form.due_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择交期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="计划数量" prop="plan_qty">
          <el-input-number v-model="form.plan_qty" :min="1" :controls="true" style="width: 100%" />
        </el-form-item>
        <el-form-item label="订单号">
          <el-input v-model="form.order_no" placeholder="留空自动生成" maxlength="50" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
          <el-button @click="goBack">取消</el-button>
        </el-form-item>
      </el-form>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createSalesOrder } from '../../api/salesOrders'

const router = useRouter()
const formRef = ref(null)
const submitting = ref(false)

const form = reactive({
  customer: '',
  due_date: '',
  plan_qty: 1,
  order_no: '',
})

const rules = {
  customer: [{ required: true, message: '请填写客户', trigger: 'blur' }],
  due_date: [{ required: true, message: '请选择交期', trigger: 'change' }],
  plan_qty: [{ required: true, message: '请填写计划数量', trigger: 'change' }],
}

function goBack() {
  router.push({ name: 'warehouse-sales-orders' })
}

async function submit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    const body = {
      customer: form.customer.trim(),
      due_date: form.due_date,
      plan_qty: form.plan_qty,
    }
    if (form.order_no.trim()) body.order_no = form.order_no.trim()
    await createSalesOrder(body)
    ElMessage.success('销售订单创建成功')
    router.push({ name: 'warehouse-sales-orders' })
  } catch (err) {
    ElMessage.error(err.message || '创建失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.sales-order-create-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
  padding: 4px 0;
}

.page-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.back-btn {
  padding-left: 0;
  margin-bottom: 4px;
}

.page-title {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.page-sub {
  margin: 0;
  font-size: 13px;
  color: #909399;
}

.form-section {
  max-width: 520px;
  padding: 20px 24px;
  background: #fff;
  border-radius: 4px;
}

.create-form {
  margin-top: 8px;
}
</style>
