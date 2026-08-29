<template>
  <div class="qa-report">
    <header class="qa-header">
      <div class="qa-header-main">
        <h1 class="qa-title">品质异常明细</h1>
        <p class="qa-subtitle">报表中心 · 质量管理 · 异常记录查询</p>
      </div>
      <div class="qa-header-meta">
        <span class="meta-label">当前筛选</span>
        <el-tag size="small" effect="plain" type="warning">{{ filterSummary }}</el-tag>
        <span class="meta-count">共 {{ total }} 条</span>
      </div>
    </header>

    <section class="qa-filter-bar">
      <el-form :model="filters" inline class="filter-form">
        <el-form-item label="状态">
          <el-select
            v-model="filters.status"
            placeholder="全部状态"
            clearable
            style="width: 140px"
          >
            <el-option label="待处理" value="open" />
            <el-option label="处理中" value="processing" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section class="qa-table-section">
      <el-table
        v-loading="loading"
        :data="items"
        stripe
        border
        class="qa-table"
        empty-text="暂无品质异常记录"
      >
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="production_line" label="产线" min-width="110" />
        <el-table-column prop="process" label="工序" min-width="100" />
        <el-table-column prop="defect_type" label="缺陷类型" min-width="110" />
        <el-table-column prop="severity" label="严重程度" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="severityTagType(row.severity)" size="small">
              {{ severityLabel(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="discovered_at" label="发现时间" min-width="140">
          <template #default="{ row }">{{ formatTime(row.discovered_at) }}</template>
        </el-table-column>
        <el-table-column prop="handler" label="处理人" min-width="90">
          <template #default="{ row }">{{ row.handler || '—' }}</template>
        </el-table-column>
      </el-table>

      <div class="qa-pagination">
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
import { ElMessage } from 'element-plus'
import { fetchQualityAnomaliesList } from '../../api/quality'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

const filters = reactive({
  status: '',
})

const filterSummary = computed(() => {
  if (!filters.status) return '全部状态'
  return statusLabel(filters.status)
})

function statusLabel(status) {
  const map = {
    open: '待处理',
    processing: '处理中',
    closed: '已关闭',
  }
  return map[status] || status || '全部状态'
}

function statusTagType(status) {
  const map = {
    open: 'danger',
    processing: 'warning',
    closed: 'success',
  }
  return map[status] || 'info'
}

function severityLabel(severity) {
  const map = { critical: '严重', major: '重要', minor: '一般' }
  return map[severity] || severity
}

function severityTagType(severity) {
  if (severity === 'critical') return 'danger'
  if (severity === 'major') return 'warning'
  return 'info'
}

function formatTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadList() {
  loading.value = true
  try {
    const resp = await fetchQualityAnomaliesList({
      status: filters.status || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    items.value = resp.items || []
    total.value = resp.total ?? 0
  } catch (err) {
    ElMessage.error(err.message || '加载品质异常明细失败')
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
  filters.status = ''
  page.value = 1
  loadList()
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.qa-report {
  display: flex;
  flex-direction: column;
  gap: 0;
  min-height: calc(100vh - 120px);
  background: var(--el-bg-color);
}

.qa-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 3px solid var(--el-color-warning);
  background: linear-gradient(135deg, #fffbf0 0%, #fff 60%);
}

.qa-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  letter-spacing: 0.02em;
}

.qa-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.qa-header-meta {
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

.qa-filter-bar {
  padding: 14px 24px;
  background: var(--el-fill-color-lighter);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.filter-form {
  margin-bottom: -8px;
}

.qa-table-section {
  flex: 1;
  padding: 16px 24px 24px;
  display: flex;
  flex-direction: column;
}

.qa-table {
  width: 100%;
}

.qa-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
