<template>
  <div class="inbound-page">
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">物料入库</h1>
        <p class="page-sub">入库单查询 · 新增登记 · 状态跟踪</p>
      </div>
      <el-button type="primary" @click="openCreate">新增入库</el-button>
    </header>

    <section class="filter-bar">
      <el-input
        v-model="filters.inboundNo"
        placeholder="入库单号"
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
        start-placeholder="入库起"
        end-placeholder="入库止"
        value-format="YYYY-MM-DD"
        style="width: 260px"
      />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px">
        <el-option label="待入库" value="pending" />
        <el-option label="已入库" value="completed" />
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
        <el-table-column prop="inbound_no" label="入库单号" min-width="140" fixed="left" />
        <el-table-column prop="material_code" label="物料编码" min-width="120" />
        <el-table-column prop="material_name" label="物料名称" min-width="130" />
        <el-table-column label="规格型号" min-width="110">
          <template #default="{ row }">{{ row.spec || '—' }}</template>
        </el-table-column>
        <el-table-column prop="quantity" label="入库数量" width="100" align="right">
          <template #default="{ row }">{{ row.quantity.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="70" align="center" />
        <el-table-column prop="warehouse_name" label="仓库" min-width="110" />
        <el-table-column label="库位" width="100">
          <template #default="{ row }">{{ row.location_code || '—' }}</template>
        </el-table-column>
        <el-table-column label="入库日期" width="110">
          <template #default="{ row }">{{ formatDate(row.inbound_date) }}</template>
        </el-table-column>
        <el-table-column label="经办人" width="90">
          <template #default="{ row }">{{ row.handler || '—' }}</template>
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
      title="新增物料入库"
      width="520px"
      destroy-on-close
      @closed="resetCreateForm"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="96px"
      >
        <el-form-item label="物料" prop="materialId">
          <el-select
            v-model="createForm.materialId"
            placeholder="选择物料"
            filterable
            style="width: 100%"
            @change="onMaterialChange"
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
        <el-form-item label="入库数量" prop="quantity">
          <el-input-number
            v-model="createForm.quantity"
            :min="1"
            :max="999999"
            controls-position="right"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="单位">
          <el-input :model-value="selectedMaterial?.unit || '—'" disabled />
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
          >
            <el-option
              v-for="loc in filteredLocations"
              :key="loc.id"
              :label="loc.location_code"
              :value="loc.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="入库日期" prop="inboundDate">
          <el-date-picker
            v-model="createForm.inboundDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="经办人" prop="handler">
          <el-input v-model="createForm.handler" placeholder="经办人姓名" clearable />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="createForm.status">
            <el-radio value="pending">待入库</el-radio>
            <el-radio value="completed">已入库</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          提交
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createMaterialInbound,
  fetchLocationOptions,
  fetchMaterialInboundList,
  fetchMaterialOptions,
  fetchWarehouseOptions,
} from '../../api/warehouse'

const STATUS_MAP = { pending: '待入库', completed: '已入库' }

const filters = reactive({
  inboundNo: '',
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

const createForm = reactive({
  materialId: null,
  quantity: 1,
  warehouseId: null,
  locationId: null,
  inboundDate: new Date().toISOString().slice(0, 10),
  handler: '',
  status: 'completed',
})

const createRules = {
  materialId: [{ required: true, message: '请选择物料', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入入库数量', trigger: 'blur' }],
  warehouseId: [{ required: true, message: '请选择仓库', trigger: 'change' }],
  inboundDate: [{ required: true, message: '请选择入库日期', trigger: 'change' }],
}

const selectedMaterial = computed(() =>
  materialOptions.value.find((m) => m.id === createForm.materialId),
)

const filteredLocations = computed(() =>
  createForm.warehouseId
    ? locationOptions.value.filter((loc) => loc.warehouse_id === createForm.warehouseId)
    : [],
)

function statusLabel(status) {
  return STATUS_MAP[status] || status
}

function formatDate(value) {
  if (!value) return '—'
  return String(value).slice(0, 10)
}

function rowClassName() {
  return 'inbound-row'
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
    const data = await fetchMaterialInboundList({
      page: page.value,
      pageSize: pageSize.value,
      inboundNo: filters.inboundNo || undefined,
      materialCode: filters.materialCode || undefined,
      materialName: filters.materialName || undefined,
      status: filters.status || undefined,
      dateFrom,
      dateTo,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    ElMessage.error(err.message || '加载入库列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.inboundNo = ''
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
  createForm.inboundDate = new Date().toISOString().slice(0, 10)
  createForm.handler = ''
  createForm.status = 'completed'
  createFormRef.value?.clearValidate()
}

function onMaterialChange() {
  // spec/unit auto from selectedMaterial
}

function onWarehouseChange() {
  createForm.locationId = null
}

async function handleSubmit() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await createMaterialInbound({
      material_id: createForm.materialId,
      quantity: createForm.quantity,
      warehouse_id: createForm.warehouseId,
      location_id: createForm.locationId || null,
      inbound_date: createForm.inboundDate,
      handler: createForm.handler || null,
      status: createForm.status,
    })
    ElMessage.success('入库单已提交')
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
.inbound-page {
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

:deep(.inbound-row:hover > td) {
  background-color: #f5f9ff !important;
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
  color: #409eff;
  background: #ecf5ff;
}
</style>
