<template>
  <div class="inspection-records-page">
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">检验记录</h1>
        <p class="page-sub">品质检验单查询 · 来料/过程/出货检验追溯</p>
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
        <el-option label="出货检验" value="final" />
      </el-select>
      <el-select
        v-model="filters.inspectionResult"
        placeholder="检验结果"
        clearable
        style="width: 120px"
      >
        <el-option label="合格" value="pass" />
        <el-option label="不合格" value="fail" />
        <el-option label="让步接收" value="conditional" />
      </el-select>
      <el-input
        v-model="filters.workOrderNo"
        placeholder="关联工单"
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
      <el-input
        v-model="filters.materialName"
        placeholder="物料名称"
        clearable
        style="width: 130px"
        @keyup.enter="handleSearch"
      />
      <el-input
        v-model="filters.inspector"
        placeholder="检验人"
        clearable
        style="width: 100px"
        @keyup.enter="handleSearch"
      />
      <el-date-picker
        v-model="filters.dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="检验起"
        end-placeholder="检验止"
        value-format="YYYY-MM-DD"
        style="width: 260px"
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
        <el-table-column label="检验结果" width="100" align="center">
          <template #default="{ row }">
            <span class="result-tag" :class="'result-' + row.inspection_result">
              {{ resultLabel(row.inspection_result) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="关联工单" min-width="140">
          <template #default="{ row }">{{ row.work_order_no || '—' }}</template>
        </el-table-column>
        <el-table-column label="批次" min-width="130">
          <template #default="{ row }">{{ row.batch_no || '—' }}</template>
        </el-table-column>
        <el-table-column prop="material_code" label="物料编码" min-width="120" />
        <el-table-column prop="material_name" label="物料名称" min-width="130" />
        <el-table-column prop="inspector" label="检验人" width="90" />
        <el-table-column label="检验时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.inspected_at) }}</template>
        </el-table-column>
        <el-table-column label="不合格数量" width="110" align="right">
          <template #default="{ row }">
            <span :class="{ 'ng-qty': row.non_conforming_qty > 0 }">
              {{ row.non_conforming_qty.toLocaleString() }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '—' }}</template>
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
import { ElMessage } from 'element-plus'
import { fetchQualityInspectionRecords } from '../../api/qualityInspectionRecords'

const TYPE_MAP = {
  incoming: '来料检验',
  process: '过程检验',
  final: '出货检验',
}

const RESULT_MAP = {
  pass: '合格',
  fail: '不合格',
  conditional: '让步接收',
}

const filters = reactive({
  inspectionNo: '',
  inspectionType: '',
  inspectionResult: '',
  workOrderNo: '',
  batchNo: '',
  materialCode: '',
  materialName: '',
  inspector: '',
  dateRange: null,
})

const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

function typeLabel(value) {
  return TYPE_MAP[value] || value || '—'
}

function resultLabel(value) {
  return RESULT_MAP[value] || value || '—'
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
    const [dateFrom, dateTo] = filters.dateRange || []
    const data = await fetchQualityInspectionRecords({
      page: page.value,
      pageSize: pageSize.value,
      inspectionNo: filters.inspectionNo || undefined,
      inspectionType: filters.inspectionType || undefined,
      inspectionResult: filters.inspectionResult || undefined,
      workOrderNo: filters.workOrderNo || undefined,
      batchNo: filters.batchNo || undefined,
      materialCode: filters.materialCode || undefined,
      materialName: filters.materialName || undefined,
      inspector: filters.inspector || undefined,
      dateFrom,
      dateTo,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    ElMessage.error(err.message || '加载检验记录失败')
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
  filters.inspectionResult = ''
  filters.workOrderNo = ''
  filters.batchNo = ''
  filters.materialCode = ''
  filters.materialName = ''
  filters.inspector = ''
  filters.dateRange = null
  page.value = 1
  loadList()
}

onMounted(loadList)
</script>

<style scoped>
.inspection-records-page {
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

.result-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.result-pass {
  color: #059669;
  background: #ecfdf5;
}

.result-fail {
  color: #dc2626;
  background: #fef2f2;
}

.result-conditional {
  color: #d97706;
  background: #fffbeb;
}

.ng-qty {
  color: #dc2626;
  font-weight: 600;
}
</style>
