<template>
  <div class="audit-page">
    <el-card shadow="never" class="search-card">
      <div class="page-heading">
        <h2 class="page-title">操作审计</h2>
        <p class="page-desc">登录与关键写操作记录，仅管理员可查</p>
      </div>
      <el-form :model="filters" inline class="search-form" @submit.prevent="handleSearch">
        <el-form-item label="操作人">
          <el-input
            v-model="filters.username"
            placeholder="用户名"
            clearable
            style="width: 140px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="动作">
          <el-input
            v-model="filters.action"
            placeholder="如 login / create"
            clearable
            style="width: 160px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="资源">
          <el-select v-model="filters.resource" placeholder="全部" clearable style="width: 140px">
            <el-option label="auth" value="auth" />
            <el-option label="work_order" value="work_order" />
            <el-option label="material_inbound" value="material_inbound" />
            <el-option label="material_outbound" value="material_outbound" />
            <el-option label="sales_order" value="sales_order" />
            <el-option label="message" value="message" />
            <el-option label="kanban_board" value="kanban_board" />
            <el-option label="equipment" value="equipment" />
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
        <span class="table-title">审计记录</span>
        <span v-if="total > 0" class="table-summary">共 {{ total }} 条</span>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="username" label="操作人" width="110" />
        <el-table-column prop="action" label="动作" width="100" />
        <el-table-column prop="resource" label="资源" width="140" />
        <el-table-column prop="resource_id" label="资源 ID" min-width="120">
          <template #default="{ row }">{{ row.resource_id || '—' }}</template>
        </el-table-column>
        <el-table-column prop="success" label="结果" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.success ? 'success' : 'danger'" size="small" effect="light">
              {{ row.success ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP" width="120">
          <template #default="{ row }">{{ row.ip || '—' }}</template>
        </el-table-column>
        <el-table-column label="详情" min-width="180">
          <template #default="{ row }">
            <span class="detail-text">{{ formatDetail(row.detail) }}</span>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无审计记录" />
        </template>
      </el-table>

      <div class="pagination-wrap">
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
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchAuditLogs } from '../../api/auditLogs'

const filters = reactive({
  username: '',
  action: '',
  resource: '',
})

const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

function formatTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function formatDetail(detail) {
  if (!detail || typeof detail !== 'object') return '—'
  try {
    const text = JSON.stringify(detail)
    return text.length > 80 ? `${text.slice(0, 80)}…` : text
  } catch {
    return '—'
  }
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchAuditLogs({
      page: page.value,
      pageSize: pageSize.value,
      username: filters.username.trim() || undefined,
      action: filters.action.trim() || undefined,
      resource: filters.resource || undefined,
    })
    items.value = data.items || []
    total.value = data.total ?? 0
  } catch (err) {
    items.value = []
    total.value = 0
    ElMessage.error(err?.message || '加载审计日志失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.username = ''
  filters.action = ''
  filters.resource = ''
  page.value = 1
  loadList()
}

onMounted(loadList)
</script>

<style scoped>
.audit-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-card,
.table-card {
  border-radius: 10px;
  border: 1px solid #e8ecf2;
}

.page-heading {
  margin-bottom: 12px;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.page-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.table-toolbar {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 12px;
}

.table-title {
  font-size: 15px;
  font-weight: 600;
  color: #374151;
}

.table-summary {
  font-size: 13px;
  color: #9ca3af;
}

.detail-text {
  font-size: 12px;
  color: #6b7280;
  word-break: break-all;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
