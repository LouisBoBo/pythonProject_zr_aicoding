<template>
  <div class="sales-orders-page">
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">销售订单</h1>
        <p class="page-sub">销售订单列表 · 新建</p>
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
        <el-table-column label="下单时间" width="170" show-overflow-tooltip>
          <template #default="{ row }">{{ formatDateTime(row.order_time) }}</template>
        </el-table-column>
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
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
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
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchSalesOrders } from '../../api/salesOrders'

const router = useRouter()

const filters = reactive({
  keyword: '',
  status: '',
})

const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

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
</style>
