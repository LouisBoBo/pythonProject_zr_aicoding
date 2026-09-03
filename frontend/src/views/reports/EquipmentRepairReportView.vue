<template>
  <div class="repair-report">
    <header class="repair-header">
      <div class="repair-header-main">
        <h1 class="repair-title">设备维修报表</h1>
        <p class="repair-subtitle">报表中心 · 设备维修 · 工单查询与导出</p>
      </div>
      <div class="repair-header-meta">
        <span class="meta-label">当前筛选</span>
        <el-tag size="small" effect="plain" type="warning">{{ filterSummary }}</el-tag>
        <span class="meta-count">共 {{ total }} 条</span>
      </div>
    </header>

    <section class="repair-filter-bar">
      <el-form :model="filters" inline class="filter-form">
        <el-form-item label="关键字">
          <el-input
            v-model="filters.keyword"
            placeholder="工单号 / 设备 / 故障描述"
            clearable
            style="width: 220px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="待处理" value="pending" />
            <el-option label="处理中" value="in_progress" />
            <el-option label="已完成" value="completed" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item label="报修日期">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始"
            end-placeholder="结束"
            value-format="YYYY-MM-DD"
            clearable
            style="width: 260px"
          />
        </el-form-item>
        <el-form-item label="设备编号">
          <el-input
            v-model="filters.equipmentCode"
            placeholder="精确匹配"
            clearable
            style="width: 140px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="故障分类">
          <el-select
            v-model="filters.faultCategory"
            placeholder="全部"
            clearable
            style="width: 130px"
          >
            <el-option v-for="cat in faultCategories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
          <el-button :icon="Download" :loading="exporting" @click="handleExport">导出 Excel</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section class="repair-table-section">
      <el-table
        v-loading="loading"
        :data="items"
        stripe
        border
        class="repair-table"
        empty-text="暂无设备维修记录"
        highlight-current-row
        @row-click="openDetail"
      >
        <el-table-column prop="repair_no" label="工单号" min-width="150" fixed="left" />
        <el-table-column label="设备" min-width="160">
          <template #default="{ row }">
            <div class="cell-equipment">
              <span class="equip-name">{{ row.equipment_name || '—' }}</span>
              <span class="equip-code">{{ row.equipment_code || '—' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="fault_category" label="故障分类" width="110" />
        <el-table-column prop="fault_description" label="故障描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="紧急程度" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="urgencyTagType(row.urgency)" size="small" effect="light">
              {{ urgencyLabel(row.urgency) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small" effect="light">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reporter" label="报修人" width="90" />
        <el-table-column prop="repair_person" label="维修人" width="90">
          <template #default="{ row }">{{ row.repair_person || '—' }}</template>
        </el-table-column>
        <el-table-column label="报修时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="完成时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.repair_completed_at, true) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="repair-pagination">
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

    <el-dialog
      v-model="detailVisible"
      :title="detail.repair_no ? `维修详情 · ${detail.repair_no}` : '维修详情'"
      width="780px"
      destroy-on-close
    >
      <div v-loading="detailLoading">
        <el-descriptions :column="2" border size="default">
          <el-descriptions-item label="设备名称">{{ detail.equipment_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="设备编号">{{ detail.equipment_code || '—' }}</el-descriptions-item>
          <el-descriptions-item label="故障分类">{{ detail.fault_category }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType(detail.status)" size="small">{{ statusLabel(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="紧急程度">
            <el-tag :type="urgencyTagType(detail.urgency)" size="small">{{ urgencyLabel(detail.urgency) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="报修人">{{ detail.reporter }}</el-descriptions-item>
          <el-descriptions-item label="维修人">{{ detail.repair_person || '—' }}</el-descriptions-item>
          <el-descriptions-item label="报修时间">{{ formatDateTime(detail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="开始维修">{{ formatDateTime(detail.start_time, true) }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ formatDateTime(detail.repair_completed_at, true) }}</el-descriptions-item>
          <el-descriptions-item label="故障描述" :span="2">{{ detail.fault_description }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.repair_description" label="维修描述" :span="2">
            {{ detail.repair_description }}
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="detail.parts?.length" class="parts-section">
          <h4 class="parts-title">更换配件</h4>
          <el-table :data="detail.parts" border size="small">
            <el-table-column prop="part_name" label="配件名称" min-width="120" />
            <el-table-column prop="part_spec" label="规格" min-width="100">
              <template #default="{ row }">{{ row.part_spec || '—' }}</template>
            </el-table-column>
            <el-table-column prop="quantity" label="数量" width="70" align="center" />
            <el-table-column prop="unit" label="单位" width="60" align="center" />
            <el-table-column label="单价" width="90" align="right">
              <template #default="{ row }">{{ row.unit_price?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="小计" width="90" align="right">
              <template #default="{ row }">{{ (row.unit_price * row.quantity).toFixed(2) }}</template>
            </el-table-column>
          </el-table>
          <div class="parts-total">配件费用合计：¥ {{ partsCostTotal.toFixed(2) }}</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  exportEquipmentRepairReport,
  fetchEquipmentRepairReport,
  fetchEquipmentRepairReportDetail,
} from '../../api/reports'

const faultCategories = ['机械故障', '电气故障', '液压故障', '软件故障', '其他']

const loading = ref(false)
const exporting = ref(false)
const detailLoading = ref(false)
const detailVisible = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const dateRange = ref(null)
const detail = ref({})

const filters = reactive({
  keyword: '',
  status: '',
  equipmentCode: '',
  faultCategory: '',
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const partsCostTotal = computed(() =>
  (detail.value.parts || []).reduce(
    (sum, p) => sum + (Number(p.unit_price) || 0) * (Number(p.quantity) || 0),
    0,
  ),
)

const filterSummary = computed(() => {
  const parts = []
  if (filters.keyword) parts.push(`关键字「${filters.keyword}」`)
  if (filters.status) parts.push(`状态「${statusLabel(filters.status)}」`)
  if (dateRange.value?.length === 2) parts.push(`日期 ${dateRange.value[0]} ~ ${dateRange.value[1]}`)
  if (filters.equipmentCode) parts.push(`设备「${filters.equipmentCode}」`)
  if (filters.faultCategory) parts.push(`分类「${filters.faultCategory}」`)
  return parts.length ? parts.join(' · ') : '全部工单'
})

function statusLabel(status) {
  const map = {
    pending: '待处理',
    in_progress: '处理中',
    completed: '已完成',
    closed: '已关闭',
  }
  return map[status] || status || '—'
}

function statusTagType(status) {
  const map = {
    pending: 'info',
    in_progress: 'warning',
    completed: 'success',
    closed: '',
  }
  return map[status] || 'info'
}

function urgencyLabel(urgency) {
  const map = { low: '低', normal: '普通', high: '高', urgent: '紧急' }
  return map[urgency] || urgency || '—'
}

function urgencyTagType(urgency) {
  const map = { low: 'info', normal: '', high: 'warning', urgent: 'danger' }
  return map[urgency] || 'info'
}

function formatDateTime(value, allowEmpty = false) {
  if (!value) return allowEmpty ? '—' : '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function buildQueryParams() {
  return {
    page: page.value,
    pageSize: pageSize.value,
    keyword: filters.keyword.trim() || undefined,
    status: filters.status || undefined,
    dateFrom: dateRange.value?.[0] || undefined,
    dateTo: dateRange.value?.[1] || undefined,
    equipmentCode: filters.equipmentCode.trim() || undefined,
    faultCategory: filters.faultCategory || undefined,
  }
}

async function loadList() {
  loading.value = true
  try {
    const resp = await fetchEquipmentRepairReport(buildQueryParams())
    items.value = resp.items || []
    total.value = resp.total ?? 0
  } catch (err) {
    ElMessage.error(err.message || '加载设备维修报表失败')
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function openDetail(row) {
  if (!row?.id) return
  detailVisible.value = true
  detailLoading.value = true
  detail.value = {}
  try {
    detail.value = await fetchEquipmentRepairReportDetail(row.id)
  } catch (err) {
    ElMessage.error(err.message || '加载详情失败')
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.keyword = ''
  filters.status = ''
  filters.equipmentCode = ''
  filters.faultCategory = ''
  dateRange.value = null
  page.value = 1
  loadList()
}

async function handleExport() {
  exporting.value = true
  try {
    const { page: _p, pageSize: _s, ...exportParams } = buildQueryParams()
    const blob = await exportEquipmentRepairReport(exportParams)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `equipment_repair_report_${new Date().toISOString().slice(0, 10)}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (err) {
    ElMessage.error(err.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.repair-report {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 120px);
  background: var(--el-bg-color);
}

.repair-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 3px solid var(--el-color-warning);
  background: linear-gradient(135deg, #fff8f0 0%, #fff 60%);
}

.repair-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.repair-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.repair-header-meta {
  display: flex;
  align-items: center;
  gap: 10px;
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

.repair-filter-bar {
  padding: 14px 24px;
  background: var(--el-fill-color-lighter);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.filter-form {
  margin-bottom: -8px;
}

.repair-table-section {
  flex: 1;
  padding: 16px 24px 24px;
  display: flex;
  flex-direction: column;
}

.repair-table {
  width: 100%;
}

.cell-equipment {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.equip-name {
  font-weight: 500;
}

.equip-code {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.repair-pagination {
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
}

.parts-section {
  margin-top: 20px;
}

.parts-title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 600;
}

.parts-total {
  margin-top: 10px;
  text-align: right;
  font-weight: 600;
  color: var(--el-color-warning-dark-2);
}
</style>
