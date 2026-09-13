<template>
  <div class="low-stock-page">
    <el-card shadow="never" class="search-card">
      <div class="page-heading">
        <h2 class="page-title">库存低水位预警</h2>
        <p class="page-desc">展示当前库存低于安全库存的物料，按缺口从大到小排序。缺口 = 安全库存 − 当前库存</p>
      </div>
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="仓库">
          <el-input
            v-model="filters.warehouseName"
            placeholder="仓库名称"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="物料编码或名称"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <span class="table-title">预警明细</span>
        <span v-if="total > 0" class="table-summary">共 {{ total }} 条低水位记录</span>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="material_code" label="物料编码" min-width="130" fixed="left" />
        <el-table-column prop="material_name" label="物料名称" min-width="140" />
        <el-table-column prop="warehouse_name" label="仓库" min-width="120" />
        <el-table-column prop="quantity" label="当前库存" width="110" align="right">
          <template #default="{ row }">{{ row.quantity.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="safety_stock" label="安全库存" width="100" align="right">
          <template #default="{ row }">{{ row.safety_stock.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="shortage" label="缺口数量" width="90" align="right">
          <template #default="{ row }">
            <span class="shortage-value">{{ row.shortage.toLocaleString() }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="70" align="center" />
        <el-table-column prop="updated_at" label="更新时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
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
          @size-change="loadList"
          @current-change="loadList"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchInventoryLowStockList } from '../../api/inventoryLowStock'

const filters = reactive({
  warehouseName: '',
  keyword: '',
})

const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchInventoryLowStockList({
      page: page.value,
      size: pageSize.value,
      warehouseName: filters.warehouseName || undefined,
      keyword: filters.keyword || undefined,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    ElMessage.error(err.message || '加载低水位预警列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.warehouseName = ''
  filters.keyword = ''
  page.value = 1
  loadList()
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.low-stock-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 100%;
}

.search-card,
.table-card {
  border-radius: 4px;
}

.page-heading {
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.page-title {
  margin: 0 0 4px;
  font-size: 17px;
  font-weight: 600;
  color: #303133;
}

.page-desc {
  margin: 0;
  font-size: 13px;
  color: #909399;
}

.search-form {
  margin-bottom: 0;
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
  color: #606266;
}

.shortage-value {
  color: #f56c6c;
  font-weight: 600;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
