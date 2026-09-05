<template>
  <div class="records-page">
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">物料出库记录</h1>
        <p class="page-sub">按出库时间、物料、批次、领用部门查询历史出库记录</p>
      </div>
      <el-button type="primary" @click="goCreate">新增出库</el-button>
    </header>

    <section class="filter-bar">
      <el-date-picker
        v-model="filters.dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="出库时间起"
        end-placeholder="出库时间止"
        value-format="YYYY-MM-DD"
        style="width: 260px"
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
      <el-input
        v-model="filters.batchNo"
        placeholder="批次号"
        clearable
        style="width: 140px"
        @keyup.enter="handleSearch"
      />
      <el-input
        v-model="filters.receiverDepartment"
        placeholder="领用部门"
        clearable
        style="width: 140px"
        @keyup.enter="handleSearch"
      />
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
        <el-table-column label="出库时间" width="110">
          <template #default="{ row }">{{ formatDate(row.outbound_date) }}</template>
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
        <el-table-column label="领用部门" min-width="110">
          <template #default="{ row }">{{ row.receiver_department || '—' }}</template>
        </el-table-column>
        <el-table-column label="领料人" width="90">
          <template #default="{ row }">{{ row.picker || '—' }}</template>
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
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchMaterialOutboundList } from '../../api/materialOutbound'

const STATUS_MAP = { pending: '待出库', completed: '已出库' }

const router = useRouter()

const filters = reactive({
  materialCode: '',
  materialName: '',
  batchNo: '',
  receiverDepartment: '',
  dateRange: null,
})

const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

function statusLabel(status) {
  return STATUS_MAP[status] || status
}

function formatDate(value) {
  if (!value) return '—'
  return String(value).slice(0, 10)
}

function rowClassName() {
  return 'records-row'
}

async function loadList() {
  loading.value = true
  try {
    const [dateFrom, dateTo] = filters.dateRange || []
    const data = await fetchMaterialOutboundList({
      page: page.value,
      pageSize: pageSize.value,
      materialCode: filters.materialCode || undefined,
      materialName: filters.materialName || undefined,
      batchNo: filters.batchNo || undefined,
      receiverDepartment: filters.receiverDepartment || undefined,
      dateFrom,
      dateTo,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    ElMessage.error(err.message || '加载出库记录失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.materialCode = ''
  filters.materialName = ''
  filters.batchNo = ''
  filters.receiverDepartment = ''
  filters.dateRange = null
  page.value = 1
  loadList()
}

function goCreate() {
  router.push('/warehouse/outbound')
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.records-page {
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

:deep(.records-row:hover > td) {
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
  color: #67c23a;
  background: #f0f9eb;
}
</style>
