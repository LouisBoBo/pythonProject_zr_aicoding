<template>
  <div class="purchase-page">
    <el-card shadow="never" class="search-card">
      <div class="page-heading">
        <h2 class="page-title">物料采购列表</h2>
        <p class="page-desc">查看物料的供应商联系信息与采购单价</p>
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
        <el-form-item label="供应商">
          <el-input
            v-model="filters.supplierName"
            placeholder="供应商名称"
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
        <span class="table-title">采购物料</span>
        <span v-if="total > 0" class="table-summary">共 {{ total }} 条</span>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="material_code" label="物料编码" min-width="130" fixed="left" />
        <el-table-column prop="material_name" label="物料名称" min-width="140" />
        <el-table-column prop="spec" label="规格" min-width="120">
          <template #default="{ row }">{{ row.spec || '-' }}</template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="70" />
        <el-table-column prop="purchase_price" label="采购单价" width="120" align="right">
          <template #default="{ row }">{{ formatPrice(row.purchase_price) }}</template>
        </el-table-column>
        <el-table-column prop="supplier_code" label="供应商编码" min-width="120">
          <template #default="{ row }">{{ row.supplier_code || '-' }}</template>
        </el-table-column>
        <el-table-column prop="supplier_name" label="供应商名称" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.supplier_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="supplier_contact" label="联系人" width="90">
          <template #default="{ row }">{{ row.supplier_contact || '-' }}</template>
        </el-table-column>
        <el-table-column prop="supplier_phone" label="联系电话" min-width="140">
          <template #default="{ row }">{{ row.supplier_phone || '-' }}</template>
        </el-table-column>
        <el-table-column prop="supplier_address" label="供应商地址" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">{{ row.supplier_address || '-' }}</template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无采购物料" />
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
import { fetchMaterialPurchaseList } from '../../api/materialPurchases'

const filters = reactive({
  materialCode: '',
  materialName: '',
  supplierName: '',
})

const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

function formatPrice(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return `¥${num.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  })}`
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchMaterialPurchaseList({
      page: page.value,
      pageSize: pageSize.value,
      materialCode: filters.materialCode || undefined,
      materialName: filters.materialName || undefined,
      supplierName: filters.supplierName || undefined,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    items.value = []
    total.value = 0
    ElMessage.error(err.message || '加载物料采购列表失败')
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
  filters.supplierName = ''
  page.value = 1
  loadList()
}

onMounted(loadList)
</script>

<style scoped>
.purchase-page {
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

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
