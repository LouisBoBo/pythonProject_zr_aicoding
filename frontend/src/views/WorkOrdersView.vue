<template>
  <div class="work-orders-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="工单号">
          <el-input v-model="filters.orderNo" placeholder="工单号" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="产品名">
          <el-input v-model="filters.productName" placeholder="产品名" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="生产线">
          <el-input v-model="filters.productionLine" placeholder="生产线" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="待开工" value="pending" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="filters.priority" placeholder="全部" clearable style="width: 120px">
            <el-option label="低" value="low" />
            <el-option label="普通" value="normal" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
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
        <span class="table-title">生产工单列表</span>
        <el-button type="primary" @click="openCreateDialog">新建工单</el-button>
      </div>

      <el-table v-loading="loading" :data="workOrders" stripe border style="width: 100%">
        <el-table-column prop="order_no" label="工单号" min-width="130" />
        <el-table-column prop="product_name" label="产品名称" min-width="120" />
        <el-table-column prop="product_code" label="产品编码" min-width="100">
          <template #default="{ row }">{{ row.product_code || '-' }}</template>
        </el-table-column>
        <el-table-column prop="production_line" label="生产线" min-width="90">
          <template #default="{ row }">{{ row.production_line || '-' }}</template>
        </el-table-column>
        <el-table-column prop="plan_quantity" label="计划数量" width="90" align="center" />
        <el-table-column prop="actual_quantity" label="实际数量" width="90" align="center" />
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
        <el-table-column prop="start_date" label="计划开始" width="110">
          <template #default="{ row }">{{ row.start_date || '-' }}</template>
        </el-table-column>
        <el-table-column prop="end_date" label="计划结束" width="110">
          <template #default="{ row }">{{ row.end_date || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button
              v-if="row.status === 'pending'"
              link
              type="success"
              size="small"
              @click="handleStatusChange(row, 'in_progress')"
            >
              开工
            </el-button>
            <el-button
              v-if="row.status === 'in_progress'"
              link
              type="success"
              size="small"
              @click="handleStatusChange(row, 'completed')"
            >
              完工
            </el-button>
            <el-button
              v-if="row.status === 'pending' || row.status === 'in_progress'"
              link
              type="warning"
              size="small"
              @click="handleStatusChange(row, 'cancelled')"
            >
              取消
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
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
          @size-change="loadWorkOrders"
          @current-change="loadWorkOrders"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑工单' : '新建工单'"
      width="560px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="工单号" prop="order_no">
          <el-input v-model="form.order_no" placeholder="请输入工单号" maxlength="50" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="产品名称" prop="product_name">
          <el-input v-model="form.product_name" placeholder="请输入产品名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="产品编码" prop="product_code">
          <el-input v-model="form.product_code" placeholder="请输入产品编码" maxlength="50" />
        </el-form-item>
        <el-form-item label="生产线" prop="production_line">
          <el-input v-model="form.production_line" placeholder="请输入生产线" maxlength="50" />
        </el-form-item>
        <el-form-item label="计划数量" prop="plan_quantity">
          <el-input-number v-model="form.plan_quantity" :min="1" :max="999999" style="width: 100%" />
        </el-form-item>
        <el-form-item v-if="isEdit" label="实际数量" prop="actual_quantity">
          <el-input-number v-model="form.actual_quantity" :min="0" :max="999999" style="width: 100%" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option label="低" value="low" />
            <el-option label="普通" value="normal" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人" prop="assignee">
          <el-input v-model="form.assignee" placeholder="请输入负责人" maxlength="50" />
        </el-form-item>
        <el-form-item label="计划开始" prop="start_date">
          <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="计划结束" prop="end_date">
          <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createWorkOrder,
  deleteWorkOrder,
  fetchWorkOrders,
  updateWorkOrder,
  updateWorkOrderStatus,
} from '../api/workOrders'

const router = useRouter()
const route = useRoute()

const workOrders = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(true)

const filters = reactive({
  orderNo: '',
  productName: '',
  productionLine: '',
  status: '',
  priority: '',
})

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const submitLoading = ref(false)
const formRef = ref(null)

const defaultForm = () => ({
  order_no: '',
  product_name: '',
  product_code: '',
  production_line: '',
  plan_quantity: 1,
  actual_quantity: 0,
  priority: 'normal',
  assignee: '',
  start_date: '',
  end_date: '',
  remark: '',
})

const form = ref(defaultForm())

const formRules = {
  order_no: [{ required: true, message: '请输入工单号', trigger: 'blur' }],
  product_name: [{ required: true, message: '请输入产品名称', trigger: 'blur' }],
  plan_quantity: [{ required: true, message: '请输入计划数量', trigger: 'change' }],
}

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

function resetForm() {
  form.value = defaultForm()
  editingId.value = null
  isEdit.value = false
}

function openCreateDialog() {
  resetForm()
  isEdit.value = false
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  editingId.value = row.id
  form.value = {
    order_no: row.order_no,
    product_name: row.product_name,
    product_code: row.product_code || '',
    production_line: row.production_line || '',
    plan_quantity: row.plan_quantity,
    actual_quantity: row.actual_quantity,
    priority: row.priority,
    assignee: row.assignee || '',
    start_date: row.start_date || '',
    end_date: row.end_date || '',
    remark: row.remark || '',
  }
  dialogVisible.value = true
}

function buildPayload() {
  const payload = {
    order_no: form.value.order_no.trim(),
    product_name: form.value.product_name.trim(),
    plan_quantity: form.value.plan_quantity,
    priority: form.value.priority,
  }
  if (form.value.product_code.trim()) payload.product_code = form.value.product_code.trim()
  if (form.value.production_line.trim()) payload.production_line = form.value.production_line.trim()
  if (form.value.assignee.trim()) payload.assignee = form.value.assignee.trim()
  if (form.value.start_date) payload.start_date = form.value.start_date
  if (form.value.end_date) payload.end_date = form.value.end_date
  if (form.value.remark.trim()) payload.remark = form.value.remark.trim()
  if (isEdit.value) payload.actual_quantity = form.value.actual_quantity
  return payload
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    const payload = buildPayload()
    if (isEdit.value) {
      await updateWorkOrder(editingId.value, payload)
      ElMessage.success('工单更新成功')
    } else {
      await createWorkOrder(payload)
      ElMessage.success('工单创建成功')
    }
    dialogVisible.value = false
    await loadWorkOrders()
  } catch (err) {
    if (err.message === '未登录') {
      router.push('/login')
      return
    }
    ElMessage.error(err.message || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

async function handleStatusChange(row, newStatus) {
  const actionLabels = {
    in_progress: '开工',
    completed: '完工',
    cancelled: '取消',
  }
  try {
    await ElMessageBox.confirm(
      `确认对工单 ${row.order_no} 执行「${actionLabels[newStatus]}」操作？`,
      '状态流转确认',
      { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' },
    )
    await updateWorkOrderStatus(row.id, newStatus)
    ElMessage.success('状态更新成功')
    await loadWorkOrders()
  } catch (err) {
    if (err === 'cancel' || err?.message === 'cancel') return
    if (err.message === '未登录') {
      router.push('/login')
      return
    }
    ElMessage.error(err.message || '状态更新失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除工单 ${row.order_no}？此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await deleteWorkOrder(row.id)
    ElMessage.success('删除成功')
    if (workOrders.value.length === 1 && page.value > 1) {
      page.value -= 1
    }
    await loadWorkOrders()
  } catch (err) {
    if (err === 'cancel' || err?.message === 'cancel') return
    if (err.message === '未登录') {
      router.push('/login')
      return
    }
    ElMessage.error(err.message || '删除失败')
  }
}

function handleSearch() {
  page.value = 1
  loadWorkOrders()
}

function handleReset() {
  filters.orderNo = ''
  filters.productName = ''
  filters.productionLine = ''
  filters.status = ''
  filters.priority = ''
  page.value = 1
  loadWorkOrders()
}

async function loadWorkOrders() {
  loading.value = true
  try {
    const data = await fetchWorkOrders({
      page: page.value,
      pageSize: pageSize.value,
      status: filters.status || undefined,
      priority: filters.priority || undefined,
      productionLine: filters.productionLine || undefined,
      orderNo: filters.orderNo || undefined,
      productName: filters.productName || undefined,
    })
    workOrders.value = data.items
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
  loadWorkOrders()
  if (route.query.create === '1' || route.query.create === 'true') {
    openCreateDialog()
    router.replace({ path: '/work-orders' })
  }
})
</script>

<style scoped>
.work-orders-page {
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

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
