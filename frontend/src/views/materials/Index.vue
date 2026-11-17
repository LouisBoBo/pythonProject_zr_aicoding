<template>
  <div class="master-page">
    <el-card shadow="never" class="search-card">
      <div class="page-heading">
        <h2 class="page-title">物料管理</h2>
        <p class="page-desc">按编码、名称查看物料主数据</p>
      </div>
      <el-form :model="filters" inline class="search-form" @submit.prevent="handleSearch">
        <el-form-item label="物料编码">
          <el-input
            v-model="filters.materialCode"
            placeholder="请输入物料编码"
            clearable
            style="width: 160px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="物料名称">
          <el-input
            v-model="filters.materialName"
            placeholder="请输入物料名称"
            clearable
            style="width: 160px"
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
        <span class="table-title">物料列表</span>
        <span v-if="filtered.length > 0" class="table-summary">共 {{ filtered.length }} 条</span>
      </div>

      <el-table v-loading="loading" :data="pageItems" stripe border style="width: 100%">
        <el-table-column prop="material_code" label="物料编码" min-width="140" />
        <el-table-column prop="material_name" label="物料名称" min-width="160" />
        <el-table-column prop="spec" label="规格" min-width="140">
          <template #default="{ row }">{{ row.spec || '-' }}</template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="90" />
        <template #empty>
          <el-empty description="暂无物料数据" />
        </template>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="filtered.length"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          background
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchMaterialOptions } from '../../api/warehouse'

const route = useRoute()

const filters = reactive({
  materialCode: '',
  materialName: '',
})
const applied = reactive({
  materialCode: '',
  materialName: '',
})

const allItems = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)

const filtered = computed(() => {
  const code = applied.materialCode.trim().toLowerCase()
  const name = applied.materialName.trim().toLowerCase()
  return allItems.value.filter((row) => {
    const rowCode = String(row.material_code || '').toLowerCase()
    const rowName = String(row.material_name || '').toLowerCase()
    if (code && !rowCode.includes(code)) return false
    if (name && !rowName.includes(name)) return false
    return true
  })
})

const pageItems = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})

async function loadList() {
  loading.value = true
  try {
    allItems.value = (await fetchMaterialOptions()) || []
  } catch (err) {
    allItems.value = []
    ElMessage.error(err.message || '加载物料列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  applied.materialCode = filters.materialCode
  applied.materialName = filters.materialName
  page.value = 1
}

function handleReset() {
  filters.materialCode = ''
  filters.materialName = ''
  applied.materialCode = ''
  applied.materialName = ''
  page.value = 1
}

onMounted(async () => {
  const qCode =
    typeof route.query.materialCode === 'string'
      ? route.query.materialCode.trim()
      : ''
  if (qCode) {
    filters.materialCode = qCode
    applied.materialCode = qCode
  }
  await loadList()
})
</script>

<style scoped>
.master-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 100%;
}

.search-card,
.table-card {
  border-radius: 8px;
  border: 1px solid #e8ecf1;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
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
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  align-items: center;
}

.search-form :deep(.el-form-item) {
  margin-bottom: 8px;
  margin-right: 12px;
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
