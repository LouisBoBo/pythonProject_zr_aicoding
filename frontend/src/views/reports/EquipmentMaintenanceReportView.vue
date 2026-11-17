<template>
  <div class="maintenance-report">
    <header class="maintenance-header">
      <div class="maintenance-header-main">
        <h1 class="maintenance-title">设备保养报表</h1>
        <p class="maintenance-subtitle">报表中心 · 计划执行情况 · 保养记录明细 · Excel 导出</p>
      </div>
      <div class="maintenance-header-meta">
        <span class="meta-label">当前筛选</span>
        <el-tag size="small" effect="plain" type="success">{{ filterSummary }}</el-tag>
        <span class="meta-count">明细共 {{ total }} 条</span>
      </div>
    </header>

    <section class="maintenance-filter-bar">
      <el-form :model="filters" inline class="filter-form">
        <el-form-item label="关键字">
          <el-input
            v-model="filters.keyword"
            placeholder="工单号 / 设备 / 保养人"
            clearable
            style="width: 220px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="待保养" value="pending" />
            <el-option label="保养中" value="in_progress" />
            <el-option label="已完成" value="completed" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item label="计划日期">
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
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
          <el-button :icon="Download" :loading="exporting" @click="handleExport">导出 Excel</el-button>
        </el-form-item>
      </el-form>
    </section>

    <div class="metric-cards">
      <el-card v-for="card in metricCards" :key="card.key" shadow="never" class="metric-card">
        <div class="metric-label">{{ card.label }}</div>
        <div class="metric-value" :class="{ highlight: card.highlight }">
          {{ card.value }}<span v-if="card.unit" class="metric-unit">{{ card.unit }}</span>
        </div>
      </el-card>
    </div>

    <section class="maintenance-table-section">
      <div class="table-toolbar">
        <span class="table-title">保养记录明细</span>
        <el-tag size="small" type="info">按保养项展开</el-tag>
      </div>

      <el-table
        v-loading="loading"
        :data="items"
        stripe
        border
        class="maintenance-table"
        empty-text="暂无保养记录"
      >
        <el-table-column label="设备" min-width="160" fixed="left">
          <template #default="{ row }">
            <div class="cell-equipment">
              <span class="equip-name">{{ row.equipment_name || '—' }}</span>
              <span class="equip-code">{{ row.equipment_code || '—' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="plan_name" label="保养计划" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.plan_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="maintainer" label="保养人" width="100">
          <template #default="{ row }">{{ row.maintainer || '—' }}</template>
        </el-table-column>
        <el-table-column label="保养时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.maintenance_time) }}</template>
        </el-table-column>
        <el-table-column prop="item_name" label="保养项目" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.item_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="item_result" label="结果" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.item_result || '—' }}</template>
        </el-table-column>
        <el-table-column label="工单状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.order_status)" size="small" effect="light">
              {{ statusLabel(row.order_status) }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div class="maintenance-pagination">
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
import { computed, onMounted, reactive, ref } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  exportEquipmentMaintenanceReport,
  fetchEquipmentMaintenanceReport,
} from '../../api/reports/equipmentMaintenanceReport.js'

function defaultDateRange() {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 6)
  const fmt = (d) => {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }
  return [fmt(start), fmt(end)]
}

const loading = ref(false)
const exporting = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const dateRange = ref(defaultDateRange())
const summary = reactive({
  due_total: 0,
  completed: 0,
  not_done: 0,
  completion_rate: 0,
})

const filters = reactive({
  keyword: '',
  status: '',
  equipmentCode: '',
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const metricCards = computed(() => [
  { key: 'due', label: '应保养', value: summary.due_total, highlight: true },
  { key: 'done', label: '已保养', value: summary.completed },
  { key: 'pending', label: '未保养', value: summary.not_done },
  {
    key: 'rate',
    label: '完成率',
    value: summary.completion_rate.toFixed(1),
    unit: '%',
  },
])

const filterSummary = computed(() => {
  const parts = []
  if (filters.keyword) parts.push(`关键字「${filters.keyword}」`)
  if (filters.status) parts.push(`状态「${statusLabel(filters.status)}」`)
  if (dateRange.value?.length === 2) parts.push(`日期 ${dateRange.value[0]} ~ ${dateRange.value[1]}`)
  if (filters.equipmentCode) parts.push(`设备「${filters.equipmentCode}」`)
  return parts.length ? parts.join(' · ') : '全部工单'
})

function statusLabel(status) {
  const map = {
    pending: '待保养',
    in_progress: '保养中',
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

function formatDateTime(value) {
  if (!value) return '—'
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
  }
}

async function loadList() {
  loading.value = true
  try {
    const resp = await fetchEquipmentMaintenanceReport(buildQueryParams())
    items.value = resp.items || []
    total.value = resp.total ?? 0
    const s = resp.summary || {}
    summary.due_total = s.due_total ?? 0
    summary.completed = s.completed ?? 0
    summary.not_done = s.not_done ?? 0
    summary.completion_rate = s.completion_rate ?? 0
  } catch (err) {
    ElMessage.error(err.message || '加载设备保养报表失败')
    items.value = []
    total.value = 0
    summary.due_total = 0
    summary.completed = 0
    summary.not_done = 0
    summary.completion_rate = 0
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
  filters.equipmentCode = ''
  dateRange.value = defaultDateRange()
  page.value = 1
  loadList()
}

async function handleExport() {
  exporting.value = true
  try {
    const { page: _p, pageSize: _s, ...exportParams } = buildQueryParams()
    const blob = await exportEquipmentMaintenanceReport(exportParams)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `equipment_maintenance_report_${new Date().toISOString().slice(0, 10)}.xlsx`
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
.maintenance-report {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 120px);
  background: var(--el-bg-color);
}

.maintenance-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 3px solid var(--el-color-success);
  background: linear-gradient(135deg, #f0fff4 0%, #fff 60%);
}

.maintenance-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.maintenance-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.maintenance-header-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.meta-label {
  color: var(--el-text-color-secondary);
}

.meta-count {
  color: var(--el-text-color-regular);
}

.maintenance-filter-bar {
  padding: 16px 24px 0;
}

.filter-form {
  flex-wrap: wrap;
}

.metric-cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  padding: 16px 24px 0;
}

.metric-card {
  border-radius: 8px;
}

.metric-card :deep(.el-card__body) {
  padding: 16px 18px;
}

.metric-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.metric-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.2;
}

.metric-value.highlight {
  color: var(--el-color-success);
}

.metric-unit {
  margin-left: 4px;
  font-size: 14px;
  font-weight: 500;
}

.maintenance-table-section {
  flex: 1;
  padding: 16px 24px 24px;
}

.table-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.table-title {
  font-size: 15px;
  font-weight: 600;
}

.maintenance-table {
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

.maintenance-pagination {
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

@media (max-width: 960px) {
  .metric-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
