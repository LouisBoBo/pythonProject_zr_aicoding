<template>
  <div class="wip-report-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="待开工" value="pending" />
            <el-option label="进行中" value="in_progress" />
          </el-select>
        </el-form-item>
        <el-form-item label="工序">
          <el-select v-model="filters.process" placeholder="全部" clearable style="width: 140px">
            <el-option v-for="p in processOptions" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="计划开始">
          <el-date-picker
            v-model="filters.startDate"
            type="date"
            placeholder="起始日期"
            value-format="YYYY-MM-DD"
            clearable
            style="width: 150px"
          />
        </el-form-item>
        <el-form-item label="计划结束">
          <el-date-picker
            v-model="filters.endDate"
            type="date"
            placeholder="截止日期"
            value-format="YYYY-MM-DD"
            clearable
            style="width: 150px"
          />
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
          <span class="table-title">在制品报表</span>
          <el-tag size="small" type="info">口径：wip（未完工且非取消）</el-tag>
        </div>
        <el-button :icon="Download" @click="handleExport">导出</el-button>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="order_no" label="工单号" min-width="130" />
        <el-table-column prop="product_name" label="品名" min-width="140" />
        <el-table-column prop="current_process" label="工序" min-width="100">
          <template #default="{ row }">{{ row.current_process || '—' }}</template>
        </el-table-column>
        <el-table-column prop="wip_quantity" label="在制数量" width="100" align="center" />
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_date" label="计划开始" width="110">
          <template #default="{ row }">{{ row.start_date || '—' }}</template>
        </el-table-column>
        <el-table-column prop="end_date" label="计划结束" width="110">
          <template #default="{ row }">{{ row.end_date || '—' }}</template>
        </el-table-column>
        <el-table-column prop="plan_quantity" label="计划数量" width="90" align="center" />
        <el-table-column prop="actual_quantity" label="实际数量" width="90" align="center" />
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
import { onMounted, reactive, ref } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { fetchWipProcesses, fetchWipReport } from '../../api/reports'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const processOptions = ref([])

const filters = reactive({
  status: '',
  process: '',
  startDate: '',
  endDate: '',
})

function statusLabel(status) {
  const map = {
    pending: '待开工',
    in_progress: '进行中',
  }
  return map[status] || status
}

function statusTagType(status) {
  const map = {
    pending: 'info',
    in_progress: 'warning',
  }
  return map[status] || ''
}

async function loadProcesses() {
  try {
    const resp = await fetchWipProcesses()
    processOptions.value = resp.processes || []
  } catch {
    processOptions.value = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const resp = await fetchWipReport({
      page: page.value,
      pageSize: pageSize.value,
      status: filters.status || undefined,
      process: filters.process || undefined,
      startDate: filters.startDate || undefined,
      endDate: filters.endDate || undefined,
    })
    items.value = resp.items || []
    total.value = resp.total || 0
  } catch (err) {
    ElMessage.error(err.message || '加载报表失败')
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadReport()
}

function handleReset() {
  filters.status = ''
  filters.process = ''
  filters.startDate = ''
  filters.endDate = ''
  page.value = 1
  loadReport()
}

function handleExport() {
  ElMessage.info('导出功能即将上线，当前可先使用浏览器打印或截图')
}

onMounted(async () => {
  await loadProcesses()
  await loadReport()
})
</script>

<style scoped>
.wip-report-page {
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
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.table-title {
  font-size: 15px;
  font-weight: 600;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
