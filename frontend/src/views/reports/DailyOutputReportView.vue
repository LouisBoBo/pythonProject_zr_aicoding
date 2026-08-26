<template>
  <div class="daily-output-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="生产日期">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            clearable
            style="width: 260px"
          />
        </el-form-item>
        <el-form-item label="产线">
          <el-select
            v-model="filters.productionLine"
            placeholder="全部"
            clearable
            style="width: 140px"
          >
            <el-option v-for="line in lineOptions" :key="line" :label="line" :value="line" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <span class="table-title">日产报表</span>
          <el-tag size="small" type="info">按日 / 产线 / 产品聚合</el-tag>
        </div>
        <div class="toolbar-right">
          <span class="sum-text">计划合计 {{ planSum }}</span>
          <span class="sum-text">实际合计 {{ actualSum }}</span>
          <span class="sum-text">不良合计 {{ defectSum }}</span>
          <el-button :icon="Download" @click="handleExport">导出</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="report_date" label="生产日期" width="120" />
        <el-table-column prop="production_line" label="产线" min-width="110" />
        <el-table-column prop="product_code" label="产品编码" min-width="120">
          <template #default="{ row }">{{ row.product_code || '—' }}</template>
        </el-table-column>
        <el-table-column prop="product_name" label="产品名称" min-width="140">
          <template #default="{ row }">{{ row.product_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="plan_qty" label="计划产量" width="100" align="right" />
        <el-table-column prop="actual_qty" label="实际产量" width="100" align="right" />
        <el-table-column prop="defect_qty" label="不良数" width="90" align="right" />
        <el-table-column prop="achievement_rate" label="达成率" width="100" align="right">
          <template #default="{ row }">{{ formatRate(row.achievement_rate) }}</template>
        </el-table-column>
        <el-table-column prop="defect_rate" label="不良率" width="100" align="right">
          <template #default="{ row }">{{ formatRate(row.defect_rate) }}</template>
        </el-table-column>
        <el-table-column prop="area_output" label="面积产出" width="110" align="right">
          <template #default="{ row }">{{ Number(row.area_output || 0).toFixed(2) }}</template>
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
          @size-change="loadReport"
          @current-change="loadReport"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { fetchDailyOutputLines, fetchDailyOutputReport } from '../../api/reports'

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
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const lineOptions = ref([])
const planSum = ref(0)
const actualSum = ref(0)
const defectSum = ref(0)
const dateRange = ref(defaultDateRange())

const filters = reactive({
  productionLine: '',
})

const dateFrom = computed(() => (dateRange.value && dateRange.value[0]) || '')
const dateTo = computed(() => (dateRange.value && dateRange.value[1]) || '')

function formatRate(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return `${n.toFixed(2)}%`
}

async function loadLines() {
  try {
    const resp = await fetchDailyOutputLines()
    lineOptions.value = resp.lines || []
  } catch {
    lineOptions.value = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const resp = await fetchDailyOutputReport({
      page: page.value,
      pageSize: pageSize.value,
      dateFrom: dateFrom.value || undefined,
      dateTo: dateTo.value || undefined,
      productionLine: filters.productionLine || undefined,
    })
    items.value = resp.items || []
    total.value = resp.total || 0
    planSum.value = resp.plan_qty_sum || 0
    actualSum.value = resp.actual_qty_sum || 0
    defectSum.value = resp.defect_qty_sum || 0
  } catch (err) {
    ElMessage.error(err.message || '加载报表失败')
    items.value = []
    total.value = 0
    planSum.value = 0
    actualSum.value = 0
    defectSum.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadReport()
}

function handleReset() {
  dateRange.value = defaultDateRange()
  filters.productionLine = ''
  page.value = 1
  loadReport()
}

function handleExport() {
  ElMessage.info('导出功能即将上线，当前可先使用浏览器打印或截图')
}

onMounted(async () => {
  await loadLines()
  await loadReport()
})
</script>

<style scoped>
.daily-output-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.search-card,
.table-card {
  border-radius: 4px;
}

.search-form {
  margin-bottom: -8px;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.table-title {
  font-size: 15px;
  font-weight: 600;
}

.sum-text {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
