<template>
  <div class="outbound-page">
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">物料出库</h1>
        <p class="page-sub">生产领料出库 · 单号自动生成 · 库存余量校验</p>
      </div>
      <el-button type="primary" @click="openCreate">新增出库</el-button>
    </header>

    <section class="filter-bar">
      <el-input
        v-model="filters.outboundNo"
        placeholder="出库单号"
        clearable
        style="width: 160px"
        @keyup.enter="handleSearch"
      />
      <el-input
        v-model="filters.materialCode"
        placeholder="物料编码"
        clearable
        style="width: 140px"
        @keyup.enter="handleSearch"
      />
      <el-input
        v-model="filters.materialName"
        placeholder="物料名称"
        clearable
        style="width: 140px"
        @keyup.enter="handleSearch"
      />
      <el-date-picker
        v-model="filters.dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="出库起"
        end-placeholder="出库止"
        value-format="YYYY-MM-DD"
        style="width: 260px"
      />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px">
        <el-option label="待出库" value="pending" />
        <el-option label="已出库" value="completed" />
      </el-select>
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
    </section>

    <section class="table-section">
      <el-table
        v-loading="loading"
        :data="items"
        border
        :row-class-name="rowClassName"
        style="width: 100%"
      >
        <el-table-column prop="outbound_no" label="出库单号" min-width="150" fixed="left" />
        <el-table-column label="出库类型" width="130">
          <template #default>{{ outboundTypeLabel }}</template>
        </el-table-column>
        <el-table-column prop="material_code" label="物料编码" min-width="120" />
        <el-table-column prop="material_name" label="物料名称" min-width="130" />
        <el-table-column label="批次" width="120">
          <template #default="{ row }">{{ row.batch_no || '—' }}</template>
        </el-table-column>
        <el-table-column label="规格型号" min-width="110">
          <template #default="{ row }">{{ row.spec || '—' }}</template>
        </el-table-column>
        <el-table-column prop="quantity" label="出库数量" width="100" align="right">
          <template #default="{ row }">{{ row.quantity.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="70" align="center" />
        <el-table-column prop="warehouse_name" label="仓库" min-width="110" />
        <el-table-column label="库位" width="100">
          <template #default="{ row }">{{ row.location_code || '—' }}</template>
        </el-table-column>
        <el-table-column label="领料人" width="90">
          <template #default="{ row }">{{ row.picker || '—' }}</template>
        </el-table-column>
        <el-table-column label="接收部门" min-width="110">
          <template #default="{ row }">{{ row.receiver_department || '—' }}</template>
        </el-table-column>
        <el-table-column label="出库日期" width="110">
          <template #default="{ row }">{{ formatDate(row.outbound_date) }}</template>
        </el-table-column>
        <el-table-column label="备注" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center" fixed="right">
          <template #default="{ row }">
            <span class="status-tag" :class="'st-' + row.status">
              {{ statusLabel(row.status) }}
            </span>
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
      v-model="createVisible"
      title="新增生产领料出库"
      width="560px"
      destroy-on-close
      @closed="resetCreateForm"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="96px"
      >
        <el-form-item label="出库类型">
          <el-input :model-value="outboundTypeLabel" disabled />
        </el-form-item>
        <el-form-item label="物料" prop="materialId">
          <el-select
            v-model="createForm.materialId"
            placeholder="选择物料"
            filterable
            style="width: 100%"
            @change="onStockContextChange"
          >
            <el-option
              v-for="m in materialOptions"
              :key="m.id"
              :label="`${m.material_code} · ${m.material_name}`"
              :value="m.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="规格型号">
          <el-input :model-value="selectedMaterial?.spec || '—'" disabled />
        </el-form-item>
        <el-form-item label="批次号" prop="batchNo">
          <el-input v-model="createForm.batchNo" placeholder="物料批次号" clearable />
        </el-form-item>
        <el-form-item label="仓库" prop="warehouseId">
          <el-select
            v-model="createForm.warehouseId"
            placeholder="选择仓库"
            style="width: 100%"
            @change="onWarehouseChange"
          >
            <el-option
              v-for="wh in warehouseOptions"
              :key="wh.id"
              :label="wh.name"
              :value="wh.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="库位">
          <el-select
            v-model="createForm.locationId"
            placeholder="可选库位"
            clearable
            filterable
            style="width: 100%"
            @change="onStockContextChange"
          >
            <el-option
              v-for="loc in filteredLocations"
              :key="loc.id"
              :label="loc.location_code"
              :value="loc.id"
            />
          </el-select>
        </el-form-item>

        <el-alert
          v-if="stockHint.visible"
          :title="stockHint.message"
          :type="stockHint.type"
          :closable="false"
          show-icon
          class="stock-alert"
        />

        <el-form-item label="出库数量" prop="quantity">
          <el-input-number
            v-model="createForm.quantity"
            :min="1"
            :max="999999"
            controls-position="right"
            style="width: 100%"
            @change="validateQuantityAgainstStock"
          />
        </el-form-item>
        <el-form-item label="单位">
          <el-input :model-value="selectedMaterial?.unit || stockBalance.unit || '—'" disabled />
        </el-form-item>
        <el-form-item label="领料人" prop="picker">
          <el-input v-model="createForm.picker" placeholder="领料人姓名" clearable />
        </el-form-item>
        <el-form-item label="接收部门" prop="receiverDepartment">
          <el-input v-model="createForm.receiverDepartment" placeholder="接收部门" clearable />
        </el-form-item>
        <el-form-item label="出库日期" prop="outboundDate">
          <el-date-picker
            v-model="createForm.outboundDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="createForm.remark"
            type="textarea"
            :rows="2"
            placeholder="可选备注"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="createForm.status">
            <el-radio value="pending">待出库</el-radio>
            <el-radio value="completed">已出库</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" :disabled="submitBlocked" @click="handleSubmit">
          提交
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createMaterialOutbound,
  fetchMaterialOutboundList,
  fetchMaterialOutboundStockBalance,
} from '../../api/materialOutbound'
import {
  fetchLocationOptions,
  fetchMaterialOptions,
  fetchWarehouseOptions,
} from '../../api/warehouse'

const OUTBOUND_TYPE_LABEL = '生产领料出库'
const STATUS_MAP = { pending: '待出库', completed: '已出库' }

const outboundTypeLabel = OUTBOUND_TYPE_LABEL

const filters = reactive({
  outboundNo: '',
  materialCode: '',
  materialName: '',
  status: '',
  dateRange: null,
})

const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const createVisible = ref(false)
const submitting = ref(false)
const createFormRef = ref(null)
const materialOptions = ref([])
const warehouseOptions = ref([])
const locationOptions = ref([])
const stockBalance = reactive({ available: null, unit: '' })
const stockLoading = ref(false)
const quantityOverStock = ref(false)

const createForm = reactive({
  materialId: null,
  quantity: 1,
  warehouseId: null,
  locationId: null,
  batchNo: '',
  outboundDate: new Date().toISOString().slice(0, 10),
  picker: '',
  receiverDepartment: '',
  remark: '',
  status: 'completed',
})

const createRules = {
  materialId: [{ required: true, message: '请选择物料', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入出库数量', trigger: 'blur' }],
  warehouseId: [{ required: true, message: '请选择仓库', trigger: 'change' }],
  outboundDate: [{ required: true, message: '请选择出库日期', trigger: 'change' }],
  picker: [{ required: true, message: '请输入领料人', trigger: 'blur' }],
  receiverDepartment: [{ required: true, message: '请输入接收部门', trigger: 'blur' }],
}

const selectedMaterial = computed(() =>
  materialOptions.value.find((m) => m.id === createForm.materialId),
)

const filteredLocations = computed(() =>
  createForm.warehouseId
    ? locationOptions.value.filter((loc) => loc.warehouse_id === createForm.warehouseId)
    : [],
)

const stockHint = computed(() => {
  if (!createForm.materialId || !createForm.warehouseId) {
    return { visible: false, type: 'info', message: '' }
  }
  if (stockLoading.value) {
    return { visible: true, type: 'info', message: '正在查询库存余量…' }
  }
  if (stockBalance.available === null) {
    return { visible: false, type: 'info', message: '' }
  }
  const unit = stockBalance.unit || selectedMaterial.value?.unit || '件'
  const available = Number(stockBalance.available)
  const qty = Number(createForm.quantity || 0)
  if (createForm.status === 'completed' && qty > available) {
    return {
      visible: true,
      type: 'error',
      message: `库存不足：当前可用 ${available.toLocaleString()} ${unit}，出库 ${qty.toLocaleString()} ${unit}`,
    }
  }
  if (available <= 0) {
    return {
      visible: true,
      type: 'warning',
      message: `当前库存为 0 ${unit}，请确认后再出库`,
    }
  }
  return {
    visible: true,
    type: 'success',
    message: `当前可用库存：${available.toLocaleString()} ${unit}`,
  }
})

const submitBlocked = computed(
  () =>
    createForm.status === 'completed'
    && createForm.materialId
    && createForm.warehouseId
    && stockBalance.available !== null
    && Number(createForm.quantity) > Number(stockBalance.available),
)

function statusLabel(status) {
  return STATUS_MAP[status] || status
}

function formatDate(value) {
  if (!value) return '—'
  return String(value).slice(0, 10)
}

function rowClassName() {
  return 'outbound-row'
}

async function loadOptions() {
  try {
    const [materials, warehouses, locations] = await Promise.all([
      fetchMaterialOptions(),
      fetchWarehouseOptions(),
      fetchLocationOptions(),
    ])
    materialOptions.value = materials || []
    warehouseOptions.value = warehouses || []
    locationOptions.value = locations || []
  } catch (err) {
    ElMessage.error(err.message || '加载选项失败')
  }
}

async function loadList() {
  loading.value = true
  try {
    const [dateFrom, dateTo] = filters.dateRange || []
    const data = await fetchMaterialOutboundList({
      page: page.value,
      pageSize: pageSize.value,
      outboundNo: filters.outboundNo || undefined,
      materialCode: filters.materialCode || undefined,
      materialName: filters.materialName || undefined,
      status: filters.status || undefined,
      dateFrom,
      dateTo,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    ElMessage.error(err.message || '加载出库列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.outboundNo = ''
  filters.materialCode = ''
  filters.materialName = ''
  filters.status = ''
  filters.dateRange = null
  page.value = 1
  loadList()
}

function openCreate() {
  createVisible.value = true
}

function resetCreateForm() {
  createForm.materialId = null
  createForm.quantity = 1
  createForm.warehouseId = null
  createForm.locationId = null
  createForm.batchNo = ''
  createForm.outboundDate = new Date().toISOString().slice(0, 10)
  createForm.picker = ''
  createForm.receiverDepartment = ''
  createForm.remark = ''
  createForm.status = 'completed'
  stockBalance.available = null
  stockBalance.unit = ''
  quantityOverStock.value = false
  createFormRef.value?.clearValidate()
}

function onWarehouseChange() {
  createForm.locationId = null
  onStockContextChange()
}

async function onStockContextChange() {
  stockBalance.available = null
  stockBalance.unit = ''
  quantityOverStock.value = false
  if (!createForm.materialId || !createForm.warehouseId) return

  stockLoading.value = true
  try {
    const data = await fetchMaterialOutboundStockBalance({
      materialId: createForm.materialId,
      warehouseId: createForm.warehouseId,
      locationId: createForm.locationId || undefined,
    })
    stockBalance.available = data.available_quantity
    stockBalance.unit = data.unit || ''
    validateQuantityAgainstStock()
  } catch (err) {
    ElMessage.warning(err.message || '库存余量查询失败')
  } finally {
    stockLoading.value = false
  }
}

function validateQuantityAgainstStock() {
  if (stockBalance.available === null) {
    quantityOverStock.value = false
    return
  }
  quantityOverStock.value = Number(createForm.quantity) > Number(stockBalance.available)
}

watch(
  () => createForm.status,
  () => validateQuantityAgainstStock(),
)

async function handleSubmit() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  if (submitBlocked.value) {
    ElMessage.error(stockHint.value.message || '出库数量超过库存余量')
    return
  }

  submitting.value = true
  try {
    await createMaterialOutbound({
      material_id: createForm.materialId,
      quantity: createForm.quantity,
      warehouse_id: createForm.warehouseId,
      location_id: createForm.locationId || null,
      batch_no: createForm.batchNo || null,
      outbound_date: createForm.outboundDate,
      picker: createForm.picker || null,
      receiver_department: createForm.receiverDepartment || null,
      remark: createForm.remark || null,
      status: createForm.status,
    })
    ElMessage.success('出库单已提交')
    createVisible.value = false
    page.value = 1
    loadList()
  } catch (err) {
    ElMessage.error(err.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await loadOptions()
  loadList()
})
</script>

<style scoped>
.outbound-page {
  display: flex;
  flex-direction: column;
  gap: 0;
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

.stock-alert {
  margin: 0 0 16px 96px;
  max-width: calc(100% - 96px);
}

:deep(.outbound-row:hover > td) {
  background-color: #fff7f0 !important;
}

.status-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 20px;
}

.st-pending {
  color: #e6a23c;
  background: #fdf6ec;
}

.st-completed {
  color: #67c23a;
  background: #f0f9eb;
}
</style>
