<template>
  <div class="sales-orders-page">
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">销售订单与发货</h1>
        <p class="page-sub">销售订单列表 · 新建 · 登记发货数量与时间</p>
      </div>
      <el-button type="primary" @click="openCreate">新建销售订单</el-button>
    </header>

    <section class="filter-bar">
      <el-input
        v-model="filters.keyword"
        placeholder="订单号 / 客户"
        clearable
        style="width: 200px"
        @keyup.enter="handleSearch"
      />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px">
        <el-option label="进行中" value="open" />
        <el-option label="已关单" value="closed" />
      </el-select>
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
    </section>

    <section class="table-section">
      <div class="table-toolbar">
        <span class="table-title">销售订单列表</span>
        <span v-if="total > 0" class="table-summary">共 {{ total }} 条</span>
      </div>

      <el-empty
        v-if="!loading && total === 0"
        description="暂无销售订单，可点击「新建销售订单」创建"
        :image-size="80"
      />

      <el-table
        v-else
        v-loading="loading"
        :data="items"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column prop="order_no" label="订单号" min-width="140" fixed="left" />
        <el-table-column prop="customer" label="客户" min-width="160" show-overflow-tooltip />
        <el-table-column label="交期" width="120">
          <template #default="{ row }">{{ formatDate(row.due_date) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.order_closed" type="success" size="small">已关单</el-tag>
            <el-tag v-else type="primary" size="small">进行中</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="plan_qty" label="计划数量" width="100" align="right">
          <template #default="{ row }">{{ row.plan_qty.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="shipped_qty" label="已发数量" width="100" align="right">
          <template #default="{ row }">{{ row.shipped_qty.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="remaining_shippable" label="剩余可发" width="100" align="right">
          <template #default="{ row }">{{ row.remaining_shippable.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="登记发货数量" width="120" align="right">
          <template #default="{ row }">
            {{ row.ship_register_qty != null ? row.ship_register_qty.toLocaleString() : '—' }}
          </template>
        </el-table-column>
        <el-table-column label="登记发货时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.ship_register_at) }}</template>
        </el-table-column>
        <el-table-column label="发满关单" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.order_closed" type="success" size="small">已关单</el-tag>
            <el-tag v-else type="info" size="small">未关单</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              v-if="!row.order_closed"
              type="primary"
              link
              size="small"
              @click="openShipDialog(row)"
            >
              登记发货
            </el-button>
            <span v-else class="muted-text">—</span>
            <el-button type="primary" link size="small" @click="openShipments(row)">
              发货记录
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="total > 0" class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="loadList"
          @current-change="loadList"
        />
      </div>
    </section>

    <el-dialog v-model="createVisible" title="新建销售订单" width="480px" destroy-on-close>
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="90px">
        <el-form-item label="客户" prop="customer">
          <el-input v-model="createForm.customer" placeholder="客户名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="交期" prop="due_date">
          <el-date-picker
            v-model="createForm.due_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择交期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="计划数量" prop="plan_qty">
          <el-input-number
            v-model="createForm.plan_qty"
            :min="1"
            :controls="true"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="订单号">
          <el-input v-model="createForm.order_no" placeholder="留空自动生成" maxlength="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createSubmitting" @click="submitCreate">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="shipVisible"
      :title="shipTarget ? `登记发货 · ${shipTarget.order_no}` : '登记发货'"
      width="440px"
      destroy-on-close
    >
      <p v-if="shipTarget" class="ship-hint">
        剩余可发：<strong>{{ shipTarget.remaining_shippable.toLocaleString() }}</strong>
      </p>
      <el-form label-width="110px">
        <el-form-item label="登记发货数量" required>
          <el-input-number
            v-model="shipForm.ship_qty"
            :min="1"
            :max="shipTarget?.remaining_shippable || 1"
            :controls="false"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="登记发货时间" required>
          <el-date-picker
            v-model="shipForm.shipped_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="选择时间"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="shipVisible = false">取消</el-button>
        <el-button type="primary" :loading="shipSubmitting" @click="submitShip">登记</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="recordsVisible" :title="recordsTitle" size="420px">
      <el-table v-loading="recordsLoading" :data="shipmentRecords" border size="small">
        <el-table-column prop="ship_qty" label="发货数量" width="100" align="right" />
        <el-table-column label="发货时间" min-width="160">
          <template #default="{ row }">{{ formatDateTime(row.shipped_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!recordsLoading && shipmentRecords.length === 0" description="暂无发货记录" />
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createSalesOrder,
  fetchOrderShipments,
  fetchSalesOrders,
  registerOrderShipment,
} from '../../api/salesOrders'

const filters = reactive({
  keyword: '',
  status: '',
})

const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const createVisible = ref(false)
const createSubmitting = ref(false)
const createFormRef = ref(null)
const createForm = reactive({
  customer: '',
  due_date: '',
  plan_qty: 1,
  order_no: '',
})
const createRules = {
  customer: [{ required: true, message: '请填写客户', trigger: 'blur' }],
  due_date: [{ required: true, message: '请选择交期', trigger: 'change' }],
  plan_qty: [{ required: true, message: '请填写计划数量', trigger: 'change' }],
}

const shipVisible = ref(false)
const shipSubmitting = ref(false)
const shipTarget = ref(null)
const shipForm = reactive({
  ship_qty: 1,
  shipped_at: '',
})

const recordsVisible = ref(false)
const recordsLoading = ref(false)
const shipmentRecords = ref([])
const recordsOrderNo = ref('')

const recordsTitle = computed(() =>
  recordsOrderNo.value ? `发货记录 · ${recordsOrderNo.value}` : '发货记录',
)

function formatDate(value) {
  if (!value) return '—'
  return String(value).slice(0, 10)
}

function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value).slice(0, 16).replace('T', ' ')
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function defaultShipAt() {
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}:00`
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchSalesOrders({
      page: page.value,
      size: pageSize.value,
      keyword: filters.keyword || undefined,
      status: filters.status || undefined,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    ElMessage.error(err.message || '加载销售订单失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.keyword = ''
  filters.status = ''
  page.value = 1
  loadList()
}

function openCreate() {
  createForm.customer = ''
  createForm.due_date = ''
  createForm.plan_qty = 1
  createForm.order_no = ''
  createVisible.value = true
}

async function submitCreate() {
  if (!createFormRef.value) return
  try {
    await createFormRef.value.validate()
  } catch {
    return
  }
  createSubmitting.value = true
  try {
    const body = {
      customer: createForm.customer.trim(),
      due_date: createForm.due_date,
      plan_qty: createForm.plan_qty,
    }
    if (createForm.order_no.trim()) body.order_no = createForm.order_no.trim()
    await createSalesOrder(body)
    ElMessage.success('销售订单创建成功')
    createVisible.value = false
    page.value = 1
    await loadList()
  } catch (err) {
    ElMessage.error(err.message || '创建失败')
  } finally {
    createSubmitting.value = false
  }
}

function openShipDialog(row) {
  if (row.order_closed) {
    ElMessage.warning('订单已关单，无法继续登记发货')
    return
  }
  shipTarget.value = row
  shipForm.ship_qty = row.remaining_shippable > 0 ? 1 : 1
  shipForm.shipped_at = defaultShipAt()
  shipVisible.value = true
}

async function submitShip() {
  const row = shipTarget.value
  if (!row) return
  const qty = Number(shipForm.ship_qty)
  if (!qty || qty < 1) {
    ElMessage.warning('请填写登记发货数量')
    return
  }
  if (qty > row.remaining_shippable) {
    ElMessage.warning(`登记发货数量不能超过剩余可发（${row.remaining_shippable}）`)
    return
  }
  shipSubmitting.value = true
  try {
    const updated = await registerOrderShipment(row.id, {
      shipQty: qty,
      shippedAt: shipForm.shipped_at || undefined,
    })
    ElMessage.success(updated.order_closed ? '登记成功，订单已发满关单' : '登记发货成功')
    shipVisible.value = false
    await loadList()
  } catch (err) {
    ElMessage.error(err.message || '登记发货失败')
  } finally {
    shipSubmitting.value = false
  }
}

async function openShipments(row) {
  recordsOrderNo.value = row.order_no
  recordsVisible.value = true
  recordsLoading.value = true
  shipmentRecords.value = []
  try {
    const data = await fetchOrderShipments(row.id)
    shipmentRecords.value = data.items || []
  } catch (err) {
    ElMessage.error(err.message || '加载发货记录失败')
  } finally {
    recordsLoading.value = false
  }
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.sales-orders-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
  padding: 4px 0;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
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

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.table-section {
  background: #fff;
  border-radius: 4px;
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
  color: #909399;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.muted-text {
  color: #c0c4cc;
}

.ship-hint {
  margin: 0 0 16px;
  font-size: 13px;
  color: #606266;
}
</style>
