<template>
  <div class="sales-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">销售订单</h1>
        <p class="page-sub">建单 · 登记发货 · 超发校验 · 发满关单</p>
      </div>
      <el-button v-if="canWrite" type="primary" @click="openCreate">新建订单</el-button>
    </header>

    <el-card shadow="never" class="filter-card">
      <el-form inline @submit.prevent="handleSearch">
        <el-form-item label="关键字">
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="订单号 / 客户"
            style="width: 180px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部" style="width: 120px">
            <el-option label="开放" value="open" />
            <el-option label="已关单" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="order_no" label="订单号" min-width="140" />
        <el-table-column prop="customer" label="客户" min-width="140" />
        <el-table-column prop="due_date" label="交期" width="120" />
        <el-table-column prop="plan_qty" label="计划数量" width="100" align="right" />
        <el-table-column prop="shipped_qty" label="已发数量" width="100" align="right" />
        <el-table-column prop="remaining_shippable" label="剩余可发" width="100" align="right" />
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.order_closed || row.status === 'closed' ? 'info' : 'success'">
              {{ row.order_closed || row.status === 'closed' ? '已关单' : '开放' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="order_time" label="下单时间" width="170">
          <template #default="{ row }">{{ formatTime(row.order_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openShipments(row)">发货记录</el-button>
            <el-button
              v-if="canWrite && !row.order_closed && row.status !== 'closed'"
              link
              type="success"
              size="small"
              @click="openShip(row)"
            >
              登记发货
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无销售订单" />
        </template>
      </el-table>

      <div class="pagination-wrap">
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
    </el-card>

    <el-dialog v-model="createVisible" title="新建销售订单" width="480px" destroy-on-close>
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="100px">
        <el-form-item label="客户" prop="customer">
          <el-input v-model="createForm.customer" maxlength="100" />
        </el-form-item>
        <el-form-item label="交期" prop="dueDate">
          <el-date-picker
            v-model="createForm.dueDate"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="计划数量" prop="planQty">
          <el-input-number v-model="createForm.planQty" :min="1" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="订单号">
          <el-input v-model="createForm.orderNo" placeholder="留空自动生成" maxlength="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createSaving" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="shipVisible" title="登记发货" width="480px" destroy-on-close>
      <p class="dialog-tip">
        {{ shipTarget?.order_no }} · 剩余可发
        <strong>{{ shipTarget?.remaining_shippable ?? 0 }}</strong>
      </p>
      <el-form ref="shipFormRef" :model="shipForm" :rules="shipRules" label-width="100px">
        <el-form-item label="发货数量" prop="shipQty">
          <el-input-number
            v-model="shipForm.shipQty"
            :min="1"
            :max="shipTarget?.remaining_shippable || 1"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="发货时间" prop="shippedAt">
          <el-date-picker
            v-model="shipForm.shippedAt"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="shipVisible = false">取消</el-button>
        <el-button type="primary" :loading="shipSaving" @click="handleShip">确认发货</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="recordsVisible" title="发货记录" size="420px">
      <p class="dialog-tip">订单：{{ recordsOrderNo }}</p>
      <el-table v-loading="recordsLoading" :data="shipments" border stripe size="small">
        <el-table-column prop="ship_qty" label="数量" width="80" />
        <el-table-column prop="shipped_at" label="发货时间">
          <template #default="{ row }">{{ formatTime(row.shipped_at) }}</template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无发货记录" :image-size="64" />
        </template>
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { usePermissions } from '../../composables/usePermissions'
import {
  createSalesOrder,
  fetchOrderShipments,
  fetchSalesOrders,
  registerOrderShipment,
} from '../../api/salesOrders'

const { can } = usePermissions()
const canWrite = computed(() => can('sales.write'))

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const filters = reactive({ keyword: '', status: '' })

function formatTime(v) {
  if (!v) return '—'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return String(v)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchSalesOrders({
      page: page.value,
      size: pageSize.value,
      keyword: filters.keyword.trim() || undefined,
      status: filters.status || undefined,
    })
    items.value = data.items || []
    total.value = data.total ?? 0
  } catch (err) {
    items.value = []
    total.value = 0
    ElMessage.error(err.message || '加载失败')
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

const createVisible = ref(false)
const createSaving = ref(false)
const createFormRef = ref(null)
const createForm = reactive({
  customer: '',
  dueDate: '',
  planQty: 1,
  orderNo: '',
})
const createRules = {
  customer: [{ required: true, message: '请输入客户', trigger: 'blur' }],
  dueDate: [{ required: true, message: '请选择交期', trigger: 'change' }],
  planQty: [{ required: true, message: '请输入计划数量', trigger: 'change' }],
}

function openCreate() {
  createForm.customer = ''
  createForm.dueDate = ''
  createForm.planQty = 1
  createForm.orderNo = ''
  createVisible.value = true
}

async function handleCreate() {
  const ok = await createFormRef.value?.validate().catch(() => false)
  if (!ok) return
  createSaving.value = true
  try {
    const body = {
      customer: createForm.customer.trim(),
      due_date: createForm.dueDate,
      plan_qty: createForm.planQty,
    }
    if (createForm.orderNo.trim()) body.order_no = createForm.orderNo.trim()
    await createSalesOrder(body)
    ElMessage.success('订单已创建')
    createVisible.value = false
    await loadList()
  } catch (err) {
    ElMessage.error(err.message || '创建失败')
  } finally {
    createSaving.value = false
  }
}

const shipVisible = ref(false)
const shipSaving = ref(false)
const shipTarget = ref(null)
const shipFormRef = ref(null)
const shipForm = reactive({ shipQty: 1, shippedAt: '' })
const shipRules = {
  shipQty: [{ required: true, message: '请输入发货数量', trigger: 'change' }],
}

function openShip(row) {
  shipTarget.value = row
  shipForm.shipQty = 1
  shipForm.shippedAt = ''
  shipVisible.value = true
}

async function handleShip() {
  const ok = await shipFormRef.value?.validate().catch(() => false)
  if (!ok || !shipTarget.value) return
  shipSaving.value = true
  try {
    const updated = await registerOrderShipment(shipTarget.value.id, {
      shipQty: shipForm.shipQty,
      shippedAt: shipForm.shippedAt || undefined,
    })
    const closed = updated.order_closed || updated.status === 'closed'
    ElMessage.success(closed ? '发货成功，订单已关单' : '发货登记成功')
    shipVisible.value = false
    await loadList()
  } catch (err) {
    ElMessage.error(err.message || '发货失败')
  } finally {
    shipSaving.value = false
  }
}

const recordsVisible = ref(false)
const recordsLoading = ref(false)
const recordsOrderNo = ref('')
const shipments = ref([])

async function openShipments(row) {
  recordsOrderNo.value = row.order_no
  recordsVisible.value = true
  recordsLoading.value = true
  try {
    const data = await fetchOrderShipments(row.id)
    shipments.value = data.items || []
    recordsOrderNo.value = data.order_no || row.order_no
  } catch (err) {
    shipments.value = []
    ElMessage.error(err.message || '加载发货记录失败')
  } finally {
    recordsLoading.value = false
  }
}

onMounted(loadList)
</script>

<style scoped>
.sales-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.page-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.filter-card,
.table-card {
  border-radius: 10px;
  border: 1px solid #e8ecf2;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.dialog-tip {
  margin: 0 0 12px;
  font-size: 13px;
  color: #6b7280;
}

.dialog-tip strong {
  color: #b45309;
  margin-left: 4px;
}
</style>
