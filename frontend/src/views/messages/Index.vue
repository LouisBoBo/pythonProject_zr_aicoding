<template>
  <div class="messages-page">
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">消息中心</h1>
        <p class="page-sub">系统通知 · 业务告警 · 公告消息</p>
      </div>
      <el-button type="primary" @click="openCreate">新增消息</el-button>
    </header>

    <section class="filter-section">
      <el-input
        v-model="filters.keyword"
        placeholder="搜索标题或内容"
        clearable
        style="width: 200px"
        @keyup.enter="handleSearch"
      />
      <el-select v-model="filters.category" placeholder="消息类型" clearable style="width: 130px">
        <el-option label="系统通知" value="system" />
        <el-option label="业务告警" value="alert" />
        <el-option label="公告通知" value="announcement" />
      </el-select>
      <el-select v-model="filters.level" placeholder="等级" clearable style="width: 100px">
        <el-option label="高" value="high" />
        <el-option label="中" value="medium" />
        <el-option label="低" value="low" />
      </el-select>
      <el-select v-model="filters.isRead" placeholder="阅读状态" clearable style="width: 110px">
        <el-option label="未读" :value="false" />
        <el-option label="已读" :value="true" />
      </el-select>
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
    </section>

    <section class="table-section">
      <el-table v-loading="loading" :data="items" border style="width: 100%">
        <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span :class="{ 'unread-title': !row.is_read }">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column label="内容摘要" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ summarize(row.content) }}</template>
        </el-table-column>
        <el-table-column label="消息类型" width="110" align="center">
          <template #default="{ row }">
            <span class="type-tag" :class="'type-' + row.category">
              {{ categoryLabel(row.category) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="等级" width="80" align="center">
          <template #default="{ row }">
            <span class="level-tag" :class="'level-' + row.level">
              {{ levelLabel(row.level) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="100" show-overflow-tooltip>
          <template #default="{ row }">{{ row.source || '—' }}</template>
        </el-table-column>
        <el-table-column label="发布时间" width="160" align="center">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <span class="status-tag" :class="row.is_read ? 'read' : 'unread'">
              {{ row.is_read ? '已读' : '未读' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="total > 0" class="pagination-wrap">
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

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑消息' : '新增消息'"
      width="560px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="96px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="消息类型" prop="category">
          <el-select v-model="form.category" style="width: 100%">
            <el-option label="系统通知" value="system" />
            <el-option label="业务告警" value="alert" />
            <el-option label="公告通知" value="announcement" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option label="普通" value="normal" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源">
          <el-input v-model="form.source" maxlength="50" placeholder="如：系统管理" clearable />
        </el-form-item>
        <el-form-item label="跳转链接">
          <el-input v-model="form.link" maxlength="200" placeholder="如：/work-orders" clearable />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="5" maxlength="2000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createMessage,
  deleteMessage,
  fetchMessageList,
  updateMessage,
} from '../../api/messages'

const loading = ref(false)
const saving = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const filters = reactive({
  keyword: '',
  category: '',
  level: '',
  isRead: null,
})

const form = reactive({
  title: '',
  content: '',
  category: 'system',
  priority: 'normal',
  source: '',
  link: '',
})

const formRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入内容', trigger: 'blur' }],
  category: [{ required: true, message: '请选择消息类型', trigger: 'change' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
}

const CATEGORY_LABEL = {
  system: '系统通知',
  alert: '业务告警',
  announcement: '公告通知',
}

const LEVEL_LABEL = {
  high: '高',
  medium: '中',
  low: '低',
}

function categoryLabel(value) {
  return CATEGORY_LABEL[value] || value
}

function levelLabel(value) {
  return LEVEL_LABEL[value] || value
}

function summarize(content) {
  if (!content) return '—'
  const text = content.replace(/\s+/g, ' ').trim()
  return text.length > 80 ? `${text.slice(0, 80)}…` : text
}

function formatTime(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchMessageList({
      page: page.value,
      size: pageSize.value,
      category: filters.category || undefined,
      level: filters.level || undefined,
      isRead: filters.isRead,
      keyword: filters.keyword.trim() || undefined,
    })
    items.value = data.items
    total.value = data.total
  } catch (err) {
    ElMessage.error(err.message || '加载消息失败')
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
  filters.category = ''
  filters.level = ''
  filters.isRead = null
  page.value = 1
  loadList()
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  editingId.value = row.id
  form.title = row.title
  form.content = row.content
  form.category = row.category
  form.priority = row.priority
  form.source = row.source || ''
  form.link = row.link || ''
  dialogVisible.value = true
}

function resetForm() {
  form.title = ''
  form.content = ''
  form.category = 'system'
  form.priority = 'normal'
  form.source = ''
  form.link = ''
  formRef.value?.clearValidate()
}

function buildPayload() {
  return {
    title: form.title.trim(),
    content: form.content.trim(),
    category: form.category,
    priority: form.priority,
    source: form.source.trim() || null,
    link: form.link.trim() || null,
  }
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload = buildPayload()
    if (isEdit.value) {
      await updateMessage(editingId.value, payload)
      ElMessage.success('消息已更新')
    } else {
      await createMessage(payload)
      ElMessage.success('消息已创建')
    }
    dialogVisible.value = false
    loadList()
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除消息「${row.title}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteMessage(row.id)
    ElMessage.success('消息已删除')
    if (items.value.length === 1 && page.value > 1) {
      page.value -= 1
    }
    loadList()
  } catch (err) {
    if (err !== 'cancel' && err?.message) {
      ElMessage.error(err.message || '删除失败')
    }
  }
}

onMounted(loadList)
</script>

<style scoped>
.messages-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.page-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: #909399;
}

.filter-section {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.table-section {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.unread-title {
  font-weight: 600;
  color: #303133;
}

.type-tag {
  display: inline-block;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}

.type-system {
  background: #ecf5ff;
  color: #409eff;
}

.type-alert {
  background: #fef0f0;
  color: #f56c6c;
}

.type-announcement {
  background: #f0f9eb;
  color: #67c23a;
}

.level-tag {
  display: inline-block;
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 4px;
  font-weight: 500;
}

.level-high {
  background: #fef0f0;
  color: #f56c6c;
}

.level-medium {
  background: #fdf6ec;
  color: #e6a23c;
}

.level-low {
  background: #f0f9eb;
  color: #67c23a;
}

.status-tag {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 10px;
}

.status-tag.unread {
  background: #ecf5ff;
  color: #409eff;
}

.status-tag.read {
  background: #f4f4f5;
  color: #909399;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
