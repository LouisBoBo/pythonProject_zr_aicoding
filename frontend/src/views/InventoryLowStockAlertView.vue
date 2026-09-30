<template>
  <div class="low-stock-alert-page">
    <el-card shadow="never" class="search-card">
      <div class="page-heading">
        <h2 class="page-title">低库存预警</h2>
        <p class="page-desc">展示现存量低于安全库存的物料，缺口 = 安全库存 − 现存量，按缺口降序排列</p>
      </div>
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="物料编码">
          <el-input
            v-model="filters.materialCode"
            placeholder="物料编码"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="物料名称">
          <el-input
            v-model="filters.materialName"
            placeholder="物料名称"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="仓库">
          <el-select
            v-model="filters.warehouseName"
            placeholder="全部仓库"
            clearable
            filterable
            style="width: 180px"
          >
            <el-option
              v-for="wh in warehouseOptions"
              :key="wh.id"
              :label="wh.name"
              :value="wh.name"
            />
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
        <span class="table-title">预警列表</span>
        <span v-if="total > 0" class="table-summary">共 {{ total }} 条低库存记录</span>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="material_code" label="物料编码" min-width="130" fixed="left" />
        <el-table-column prop="material_name" label="物料名称" min-width="140" />
        <el-table-column prop="warehouse_name" label="仓库" min-width="120" />
        <el-table-column prop="quantity" label="现存量" width="100" align="right">
          <template #default="{ row }">{{ row.quantity.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="safety_stock" label="安全库存" width="100" align="right">
          <template #default="{ row }">{{ row.safety_stock.toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="shortage" label="缺口" width="100" align="right">
          <template #default="{ row }">
            <span class="shortage-value">{{ row.shortage.toLocaleString() }}</span>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无低库存预警数据" />
        </template>
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
import { fetchInventoryLowStockList } from '../api/inventoryLowStock'
import { fetchWarehouseOptions } from '../api/warehouse'

const filters = reactive({
  materialCode: '',
  materialName: '',
  warehouseName: '',
})

const items = ref([])
const warehouseOptions = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

async function loadWarehouseOptions() {
  try {
    warehouseOptions.value = await fetchWarehouseOptions()
  } catch (err) {
    ElMessage.error(err.message || '加载仓库选项失败')
  }
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchInventoryLowStockList({
      page: page.value,
      pageSize: pageSize.value,
      materialCode: filters.materialCode || undefined,
      materialName: filters.materialName || undefined,
      warehouseName: filters.warehouseName || undefined,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    ElMessage.error(err.message || '加载低库存预警列表失败')
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
  filters.warehouseName = ''
  page.value = 1
  loadList()
}

onMounted(() => {
  loadWarehouseOptions()
  loadList()
})
</script>

<style scoped>
.low-stock-alert-page {
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
