<template>
  <div class="eq-report">
    <header class="eq-header">
      <div class="eq-header-main">
        <h1 class="eq-title">设备档案台账</h1>
        <p class="eq-subtitle">报表中心 · 设备管理 · MES 设备台账查询</p>
      </div>
      <div class="eq-header-meta">
        <span class="meta-label">当前筛选</span>
        <el-tag size="small" effect="plain" type="primary">{{ filterSummary }}</el-tag>
        <span class="meta-count">共 {{ total }} 条</span>
      </div>
    </header>

    <section class="eq-filter-bar">
      <el-form :model="filters" inline class="filter-form">
        <el-form-item label="设备">
          <el-select
            v-model="filters.equipmentCode"
            placeholder="全部"
            clearable
            filterable
            :loading="optionsLoading"
            no-data-text="暂无设备数据"
            style="width: 260px"
          >
            <el-option
              v-for="eq in equipmentOptions"
              :key="eq.equipment_code"
              :label="`${eq.equipment_code} · ${eq.name}`"
              :value="eq.equipment_code"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-input
            v-model="filters.department"
            placeholder="使用部门"
            clearable
            style="width: 130px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="filters.status"
            placeholder="全部状态"
            clearable
            style="width: 120px"
          >
            <el-option label="运行" value="运行" />
            <el-option label="停机" value="停机" />
            <el-option label="维修" value="维修" />
            <el-option label="报废" value="报废" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
          <el-button :icon="Download" :loading="exporting" @click="handleExport">导出</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section class="eq-table-section">
      <el-table
        v-loading="loading"
        :data="items"
        stripe
        border
        class="eq-table"
        empty-text="暂无设备台账记录"
      >
        <el-table-column prop="equipment_code" label="编号" min-width="120" fixed="left" />
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="spec_model" label="规格型号" min-width="120">
          <template #default="{ row }">{{ row.spec_model || '—' }}</template>
        </el-table-column>
        <el-table-column prop="department" label="部门" min-width="110">
          <template #default="{ row }">{{ row.department || '—' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small" effect="light">
              {{ row.status || '—' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="location" label="位置" min-width="100">
          <template #default="{ row }">{{ row.location || '—' }}</template>
        </el-table-column>
        <el-table-column prop="purchase_date" label="购置日期" width="110">
          <template #default="{ row }">{{ row.purchase_date || '—' }}</template>
        </el-table-column>
        <el-table-column prop="supplier" label="供应商" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.supplier || '—' }}</template>
        </el-table-column>
      </el-table>

      <div class="eq-pagination">
        <span class="page-info">第 {{ page }} / {{ totalPages }} 页，本页 {{ items.length }} 条</span>
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
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { exportEquipment, fetchEquipmentList } from '../../api/equipment'

const loading = ref(false)
const exporting = ref(false)
const optionsLoading = ref(false)
const items = ref([])
const equipmentOptions = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

const filters = reactive({
  equipmentCode: '',
  department: '',
  status: '',
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const filterSummary = computed(() => {
  const parts = []
  if (filters.equipmentCode) {
    const eq = equipmentOptions.value.find((item) => item.equipment_code === filters.equipmentCode)
    const label = eq ? `${eq.equipment_code} · ${eq.name}` : filters.equipmentCode
    parts.push(`设备「${label}」`)
  }
  if (filters.department) parts.push(`部门「${filters.department}」`)
  if (filters.status) parts.push(`状态「${filters.status}」`)
  return parts.length ? parts.join(' · ') : '全部设备'
})

function statusTagType(status) {
  const map = {
    运行: 'success',
    停机: 'info',
    维修: 'warning',
    报废: 'danger',
  }
  return map[status] || 'info'
}

function selectedEquipment() {
  if (!filters.equipmentCode) return null
  return equipmentOptions.value.find((item) => item.equipment_code === filters.equipmentCode) || null
}

function buildQueryParams() {
  const params = {
    page: page.value,
    pageSize: pageSize.value,
    department: filters.department.trim() || undefined,
    status: filters.status || undefined,
  }
  const eq = selectedEquipment()
  if (eq) {
    params.equipmentCode = eq.equipment_code
    params.name = eq.name
  }
  return params
}

async function loadEquipmentOptions() {
  optionsLoading.value = true
  try {
    const resp = await fetchEquipmentList({ page: 1, pageSize: 1000 })
    equipmentOptions.value = resp.items || []
  } catch (err) {
    equipmentOptions.value = []
    ElMessage.warning(err.message || '加载设备选项失败')
  } finally {
    optionsLoading.value = false
  }
}

async function loadList() {
  loading.value = true
  try {
    const resp = await fetchEquipmentList(buildQueryParams())
    items.value = resp.items || []
    total.value = resp.total ?? 0
  } catch (err) {
    ElMessage.error(err.message || '加载设备台账失败')
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.equipmentCode = ''
  filters.department = ''
  filters.status = ''
  page.value = 1
  loadList()
}

async function handleExport() {
  exporting.value = true
  try {
    const blob = await exportEquipment(buildQueryParams())
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `equipment_${new Date().toISOString().slice(0, 10)}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (err) {
    ElMessage.error(err.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

let debounceTimer = null
watch(
  () => [filters.equipmentCode, filters.department, filters.status],
  () => {
    clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      page.value = 1
      loadList()
    }, 400)
  },
)

onMounted(() => {
  loadEquipmentOptions()
  loadList()
})
</script>

<style scoped>
.eq-report {
  display: flex;
  flex-direction: column;
  gap: 0;
  min-height: calc(100vh - 120px);
  background: var(--el-bg-color);
}

.eq-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 3px solid var(--el-color-primary);
  background: linear-gradient(135deg, #f0f7ff 0%, #fff 60%);
}

.eq-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  letter-spacing: 0.02em;
}

.eq-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.eq-header-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.meta-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.meta-count {
  font-size: 13px;
  color: var(--el-text-color-regular);
  font-variant-numeric: tabular-nums;
}

.eq-filter-bar {
  padding: 14px 24px;
  background: var(--el-fill-color-lighter);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.filter-form {
  margin-bottom: -8px;
}

.eq-table-section {
  flex: 1;
  padding: 16px 24px 24px;
  display: flex;
  flex-direction: column;
}

.eq-table {
  width: 100%;
}

.eq-table :deep(.el-table__row:hover > td) {
  background-color: var(--el-color-primary-light-9) !important;
}

.eq-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.page-info {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  font-variant-numeric: tabular-nums;
}
</style>
