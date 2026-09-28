<template>
  <div class="sales-orders-page">
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">销售订单</h1>
        <p class="page-sub">订单列表 · 登记发货数量与时间 · 超发校验 · 发满关单</p>
      </div>
      <el-button type="primary" @click="goCreate">新建销售订单</el-button>
    </header>

    <section class="filter-bar">
      <el-input
        v-model="filters.keyword"
        placeholder="订单号 / 客户"
        clearable
        style="width: 200px"
        @keyup.enter="handleSearch"
      />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 130px">
        <el-option label="进行中" value="open" />
        <el-option label="已关单" value="closed" />
      </el-select>
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
    </section>

    <section class="table-section">
      <el-table v-loading="loading" :data="items" border style="width: 100%">
        <el-table-column prop="order_no" label="订单号" min-width="130" fixed="left" />
        <el-table-column prop="customer" label="客户" min-width="120" />
        <el-table-column label="交期" width="110">
          <template #default="{ row }">{{ formatDate(row.due_date) }}</template>
        </el-table-column>
        <el-table-column prop="plan_qty" label="计划数量" width="100" align="right" />
        <el-table-column prop="shipped_qty" label="已发数量" width="100" align="right" />
        <el-table-column prop="remaining_shippable" label="剩余可发" width="100" align="right" />
        <el-table-column label="登记发货数量" width="120" align="right">
          <template #default="{ row }">
            {{ row.ship_register_qty != null ? row.ship_register_qty : '—' }}
          </template>
        </el-table-column>
        <el-table-column label="登记发货时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.ship_register_at) }}</template>
        </el-table-column>
        <el-table-column label="关单" width="80" align="center">
          <template #default="{ row }">
            <span class="status-tag" :class="row.order_closed ? 'st-closed' : 'st-open'">
              {{ row.order_closed ? '是' : '否' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span class="status-tag" :class="'st-' + row.status">
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              :disabled="row.order_closed || row.status === 'closed'"
              @click="openShipDialog(row)"
            >
              登记发货
            </el-button>
            <el-button link type="primary" @click="openRecordsDialog(row)">发货记录</el-button>
          </template>
        </el-table-column>
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
    </section>

    <el-dialog
      v-model="shipVisible"
      title="登记发货"
      width="480px"
      destroy-on-close
      @closed="resetShipForm"
    >
      <p v-if="shipTarget" class="ship-hint">
        订单 {{ shipTarget.order_no }} · 剩余可发
        <strong>{{ shipTarget.remaining_shippable }}</strong>
      </p>
      <el-form ref="shipFormRef" :model="shipForm" :rules="shipRules" label-width="110px">
        <el-form-item label="登记发货数量" prop="shipQty">
          <el-input-number
            v-model="shipForm.shipQty"
            :min="1"
            :max="shipMaxQty"
            controls-position="right"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="登记发货时间" prop="shippedAt">
          <el-date-picker
            v-model="shipForm.shippedAt"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="默认当前时间"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="shipVisible = false">取消</el-button>
        <el-button type="primary" :loading="shipSubmitting" @click="submitShipment">确认登记</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="recordsVisible"
      :title="recordsTitle"
      width="560px"
      destroy-on-close
    >
      <el-table v-loading="recordsLoading" :data="shipmentRecords" border size="small">
        <el-table-column prop="ship_qty" label="发货数量" width="100" align="right" />
        <el-table-column label="发货时间" min-width="170">
          <template #default="{ row }">{{ formatDateTime(row.shipped_at) }}</template>
        </el-table-column>
      </el-table>
      <p v-if="!recordsLoading && !shipmentRecords.length" class="empty-records">暂无发货记录</p>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchOrderShipments,
  fetchSalesOrders,
  registerOrderShipment,
} from '../../api/salesOrders'

const router = useRouter()

const STATUS_MAP = { open: '进行中', closed: '已关单' }

const filters = reactive({
  keyword: '',
  status: '',
})

const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const shipVisible = ref(false)
const shipSubmitting = ref(false)
const shipFormRef = ref(null)
const shipTarget = ref(null)
const shipForm = reactive({
  shipQty: 1,
  shippedAt: '',
})

const recordsVisible = ref(false)
const recordsLoading = ref(false)
const shipmentRecords = ref([])
const recordsOrderNo = ref('')

const shipMaxQty = computed(() => {
  const n = shipTarget.value?.remaining_shippable
  return n != null && n > 0 ? n : 1
})

const recordsTitle = computed(() =>
  recordsOrderNo.value ? `发货记录 · ${recordsOrderNo.value}` : '发货记录',
)

const shipRules = {
  shipQty: [{ required: true, message: '请填写登记发货数量', trigger: 'change' }],
}

function statusLabel(status) {
  return STATUS_MAP[status] || status
}

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

function goCreate() {
  router.push({ name: 'warehouse-sales-orders-new' })
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

function openShipDialog(row) {
  if (row.order_closed || row.status === 'closed') {
    ElMessage.warning('订单已关单，无法继续登记发货')
    return
  }
  shipTarget.value = row
  shipForm.shipQty = 1
  shipForm.shippedAt = ''
  shipVisible.value = true
}

function resetShipForm() {
  shipTarget.value = null
  shipForm.shipQty = 1
  shipForm.shippedAt = ''
  shipFormRef.value?.clearValidate()
}

async function submitShipment() {
  if (!shipTarget.value) return
  const valid = await shipFormRef.value?.validate().catch(() => false)
  if (!valid) return

  if (shipForm.shipQty > shipTarget.value.remaining_shippable) {
    ElMessage.error(
      `登记发货数量不能超过剩余可发（${shipTarget.value.remaining_shippable}）`,
    )
    return
  }

  shipSubmitting.value = true
  try {
    await registerOrderShipment(shipTarget.value.id, {
      shipQty: shipForm.shipQty,
      shippedAt: shipForm.shippedAt || undefined,
    })
    ElMessage.success('发货登记成功')
    shipVisible.value = false
    loadList()
  } catch (err) {
    ElMessage.error(err.message || '登记发货失败')
  } finally {
    shipSubmitting.value = false
  }
}

async function openRecordsDialog(row) {
  recordsOrderNo.value = row.order_no
  shipmentRecords.value = []
  recordsVisible.value = true
  recordsLoading.value = true
  try {
    const data = await fetchOrderShipments(row.id)
    shipmentRecords.value = data.items || []
    if (data.order_no) recordsOrderNo.value = data.order_no
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
  min-height: calc(100vh - 120px);
  background: #f5f7fa;
  margin: -16px;
  padding: 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 16px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.page-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: #909399;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 14px 24px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.table-section {
  flex: 1;
  padding: 16px 24px 24px;
  background: #fff;
  margin: 12px 16px 16px;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.status-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 20px;
}

.st-open {
  color: #409eff;
  background: #ecf5ff;
}

.st-closed,
.st-closed.status-tag {
  color: #909399;
  background: #f4f4f5;
}

.st-open.status-tag.st-open {
  color: #67c23a;
  background: #f0f9eb;
}

.ship-hint {
  margin: 0 0 16px;
  font-size: 13px;
  color: #606266;
}

.empty-records {
  margin: 12px 0 0;
  text-align: center;
  color: #909399;
  font-size: 13px;
}
</style>
