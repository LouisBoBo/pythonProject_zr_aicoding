<template>
  <div class="anomaly-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">品质异常</h1>
        <p class="page-sub">筛选未处理异常，填写处理人与说明后关闭</p>
      </div>
    </header>

    <el-card shadow="never" class="filter-card">
      <el-form inline @submit.prevent="handleSearch">
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部" style="width: 140px">
            <el-option label="未处理" value="open" />
            <el-option label="处理中" value="processing" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="production_line" label="产线" min-width="110" />
        <el-table-column prop="process" label="工序" min-width="100" />
        <el-table-column prop="defect_type" label="缺陷类型" min-width="110" />
        <el-table-column prop="severity" label="严重度" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="light" :type="severityType(row.severity)">
              {{ severityLabel(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="discovered_at" label="发现时间" width="170">
          <template #default="{ row }">{{ formatTime(row.discovered_at) }}</template>
        </el-table-column>
        <el-table-column prop="handler" label="处理人" width="100">
          <template #default="{ row }">{{ row.handler || '—' }}</template>
        </el-table-column>
        <el-table-column prop="resolution_note" label="处理说明" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.resolution_note || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.status !== 'closed'"
              link
              type="primary"
              size="small"
              @click="openClose(row)"
            >
              关闭
            </el-button>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无品质异常" />
        </template>
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
    </el-card>

    <el-dialog v-model="closeVisible" title="关闭品质异常" width="440px" destroy-on-close>
      <p class="dialog-tip">
        {{ closeTarget?.production_line }} · {{ closeTarget?.defect_type }}
      </p>
      <el-form ref="closeFormRef" :model="closeForm" :rules="closeRules" label-width="90px">
        <el-form-item label="处理人" prop="handler">
          <el-input v-model="closeForm.handler" maxlength="50" placeholder="必填" />
        </el-form-item>
        <el-form-item label="处理说明" prop="resolutionNote">
          <el-input
            v-model="closeForm.resolutionNote"
            type="textarea"
            :rows="3"
            maxlength="500"
            placeholder="必填，说明处理结果"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeVisible = false">取消</el-button>
        <el-button type="primary" :loading="closing" @click="handleClose">确认关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { closeQualityAnomaly, fetchQualityAnomaliesList } from '../../api/quality'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const filters = reactive({ status: 'open' })

const closeVisible = ref(false)
const closing = ref(false)
const closeTarget = ref(null)
const closeFormRef = ref(null)
const closeForm = reactive({ handler: '', resolutionNote: '' })
const closeRules = {
  handler: [{ required: true, message: '请填写处理人', trigger: 'blur' }],
  resolutionNote: [{ required: true, message: '请填写处理说明', trigger: 'blur' }],
}

function statusLabel(s) {
  return { open: '未处理', processing: '处理中', closed: '已关闭' }[s] || s
}

function statusType(s) {
  if (s === 'closed') return 'success'
  if (s === 'processing') return 'warning'
  return 'danger'
}

function severityLabel(s) {
  return { critical: '严重', major: '重要', minor: '一般' }[s] || s
}

function severityType(s) {
  if (s === 'critical') return 'danger'
  if (s === 'major') return 'warning'
  return 'info'
}

function formatTime(v) {
  if (!v) return '—'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return String(v)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchQualityAnomaliesList({
      status: filters.status || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    items.value = data.items || []
    total.value = data.total ?? 0
  } catch (err) {
    items.value = []
    total.value = 0
    ElMessage.error(err.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.status = 'open'
  page.value = 1
  loadList()
}

function openClose(row) {
  closeTarget.value = row
  closeForm.handler = ''
  closeForm.resolutionNote = ''
  closeVisible.value = true
}

async function handleClose() {
  const ok = await closeFormRef.value?.validate().catch(() => false)
  if (!ok || !closeTarget.value) return
  closing.value = true
  try {
    await closeQualityAnomaly(closeTarget.value.id, {
      handler: closeForm.handler.trim(),
      resolutionNote: closeForm.resolutionNote.trim(),
    })
    ElMessage.success('已关闭')
    closeVisible.value = false
    await loadList()
  } catch (err) {
    ElMessage.error(err.message || '关闭失败')
  } finally {
    closing.value = false
  }
}

onMounted(loadList)
</script>

<style scoped>
.anomaly-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.page-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.filter-card,
.table-card {
  border-radius: 10px;
  border: 1px solid #e8ecf2;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.dialog-tip {
  margin: 0 0 12px;
  color: #6b7280;
  font-size: 13px;
}

.muted {
  color: #9ca3af;
}
</style>
