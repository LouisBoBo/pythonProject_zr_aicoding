<template>
  <div class="inspection-tasks-page">
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">检验任务</h1>
        <p class="page-sub">品质检验任务管理 · 来料/过程/成品 · 待检/合格/不合格流转</p>
      </div>
    </header>

    <section class="filter-bar">
      <el-input
        v-model="filters.inspectionNo"
        placeholder="检验单号"
        clearable
        style="width: 150px"
        @keyup.enter="handleSearch"
      />
      <el-select
        v-model="filters.inspectionType"
        placeholder="检验类型"
        clearable
        style="width: 120px"
      >
        <el-option label="来料检验" value="incoming" />
        <el-option label="过程检验" value="process" />
        <el-option label="成品检验" value="final" />
      </el-select>
      <el-select
        v-model="filters.status"
        placeholder="任务状态"
        clearable
        style="width: 120px"
      >
        <el-option label="待检" value="pending" />
        <el-option label="合格" value="passed" />
        <el-option label="不合格" value="failed" />
      </el-select>
      <el-input
        v-model="filters.workOrderNo"
        placeholder="工单号"
        clearable
        style="width: 140px"
        @keyup.enter="handleSearch"
      />
      <el-input
        v-model="filters.productCode"
        placeholder="产品编码"
        clearable
        style="width: 140px"
        @keyup.enter="handleSearch"
      />
      <el-input
        v-model="filters.batchNo"
        placeholder="批次号"
        clearable
        style="width: 130px"
        @keyup.enter="handleSearch"
      />
      <el-input
        v-model="filters.materialCode"
        placeholder="物料编码"
        clearable
        style="width: 130px"
        @keyup.enter="handleSearch"
      />
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
    </section>

    <section class="table-section">
      <el-table v-loading="loading" :data="items" border style="width: 100%">
        <el-table-column prop="inspection_no" label="检验单号" min-width="150" fixed="left" />
        <el-table-column label="检验类型" width="100" align="center">
          <template #default="{ row }">
            {{ typeLabel(row.inspection_type) }}
          </template>
        </el-table-column>
        <el-table-column label="任务状态" width="100" align="center">
          <template #default="{ row }">
            <span class="status-tag" :class="'status-' + row.status">
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="工单号" min-width="140">
          <template #default="{ row }">{{ row.work_order_no || '—' }}</template>
        </el-table-column>
        <el-table-column label="产品编码" min-width="120">
          <template #default="{ row }">{{ row.product_code || '—' }}</template>
        </el-table-column>
        <el-table-column label="批次" min-width="130">
          <template #default="{ row }">{{ row.batch_no || '—' }}</template>
        </el-table-column>
        <el-table-column prop="material_code" label="物料编码" min-width="120" />
        <el-table-column prop="material_name" label="物料名称" min-width="130" />
        <el-table-column prop="inspector" label="检验人" width="90" />
        <el-table-column label="创建/检验时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.inspected_at) }}</template>
        </el-table-column>
        <el-table-column label="备注" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button type="success" link size="small" @click="handleStatusChange(row, 'passed')">
                合格
              </el-button>
              <el-button type="danger" link size="small" @click="handleStatusChange(row, 'failed')">
                不合格
              </el-button>
            </template>
            <span v-else class="no-action">—</span>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchQualityInspectionTasks,
  updateQualityInspectionTaskStatus,
} from '../../api/qualityInspectionTasks'

const TYPE_MAP = {
  incoming: '来料检验',
  process: '过程检验',
  final: '成品检验',
}

const STATUS_MAP = {
  pending: '待检',
  passed: '合格',
  failed: '不合格',
}

const filters = reactive({
  inspectionNo: '',
  inspectionType: '',
  status: '',
  workOrderNo: '',
  productCode: '',
  batchNo: '',
  materialCode: '',
})

const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

function typeLabel(value) {
  return TYPE_MAP[value] || value || '—'
}

function statusLabel(value) {
  return STATUS_MAP[value] || value || '—'
}

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
    const data = await fetchQualityInspectionTasks({
      page: page.value,
      pageSize: pageSize.value,
      inspectionNo: filters.inspectionNo || undefined,
      inspectionType: filters.inspectionType || undefined,
      status: filters.status || undefined,
      workOrderNo: filters.workOrderNo || undefined,
      productCode: filters.productCode || undefined,
      batchNo: filters.batchNo || undefined,
      materialCode: filters.materialCode || undefined,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    ElMessage.error(err.message || '加载检验任务失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.inspectionNo = ''
  filters.inspectionType = ''
  filters.status = ''
  filters.workOrderNo = ''
  filters.productCode = ''
  filters.batchNo = ''
  filters.materialCode = ''
  page.value = 1
  loadList()
}

async function handleStatusChange(row, newStatus) {
  const actionLabels = {
    passed: '合格',
    failed: '不合格',
  }
  try {
    await ElMessageBox.confirm(
      `确认将检验任务 ${row.inspection_no} 标记为「${actionLabels[newStatus]}」？`,
      '状态流转确认',
      { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' },
    )
    await updateQualityInspectionTaskStatus(row.id, newStatus)
    ElMessage.success('状态更新成功')
    await loadList()
  } catch (err) {
    if (err === 'cancel' || err?.message === 'cancel') return
    ElMessage.error(err.message || '状态更新失败')
  }
}

onMounted(loadList)
</script>

<style scoped>
.inspection-tasks-page {
  padding: 0 4px 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-title {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.page-sub {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
  padding: 16px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.table-section {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.status-pending {
  color: #d97706;
  background: #fffbeb;
}

.status-passed {
  color: #059669;
  background: #ecfdf5;
}

.status-failed {
  color: #dc2626;
  background: #fef2f2;
}

.no-action {
  color: var(--el-text-color-placeholder);
}
</style>
