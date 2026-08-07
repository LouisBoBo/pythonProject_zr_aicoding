<template>
  <div class="kanban-boards-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="看板编码">
          <el-input v-model="filters.boardCode" placeholder="看板编码" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="看板名称">
          <el-input v-model="filters.boardName" placeholder="看板名称" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="生产线">
          <el-input v-model="filters.productionLine" placeholder="生产线" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="filters.category" placeholder="全部" clearable style="width: 120px">
            <el-option label="生产" value="production" />
            <el-option label="品质" value="quality" />
            <el-option label="设备" value="equipment" />
            <el-option label="仓储" value="warehouse" />
            <el-option label="通用" value="general" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="active" />
            <el-option label="已归档" value="archived" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <span class="table-title">看板列表</span>
        <el-button type="primary" @click="openCreateDialog">新建看板</el-button>
      </div>

      <el-table v-loading="loading" :data="boards" stripe border style="width: 100%">
        <el-table-column prop="board_code" label="看板编码" min-width="130" />
        <el-table-column prop="board_name" label="看板名称" min-width="140" />
        <el-table-column prop="category" label="分类" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ categoryLabel(row.category) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="production_line" label="生产线" min-width="90">
          <template #default="{ row }">{{ row.production_line || '-' }}</template>
        </el-table-column>
        <el-table-column prop="owner" label="负责人" min-width="80">
          <template #default="{ row }">{{ row.owner || '-' }}</template>
        </el-table-column>
        <el-table-column prop="refresh_interval" label="刷新间隔" width="100" align="center">
          <template #default="{ row }">{{ row.refresh_interval }}s</template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button
              v-if="row.status === 'draft'"
              link
              type="success"
              size="small"
              @click="handleStatusChange(row, 'active')"
            >
              发布
            </el-button>
            <el-button
              v-if="row.status === 'active'"
              link
              type="warning"
              size="small"
              @click="handleStatusChange(row, 'archived')"
            >
              归档
            </el-button>
            <el-button
              v-if="row.status === 'archived'"
              link
              type="success"
              size="small"
              @click="handleStatusChange(row, 'active')"
            >
              启用
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
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
          @size-change="loadBoards"
          @current-change="loadBoards"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑看板' : '新建看板'"
      width="560px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="看板编码" prop="board_code">
          <el-input v-model="form.board_code" placeholder="请输入看板编码" maxlength="50" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="看板名称" prop="board_name">
          <el-input v-model="form.board_name" placeholder="请输入看板名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="form.category" style="width: 100%">
            <el-option label="生产" value="production" />
            <el-option label="品质" value="quality" />
            <el-option label="设备" value="equipment" />
            <el-option label="仓储" value="warehouse" />
            <el-option label="通用" value="general" />
          </el-select>
        </el-form-item>
        <el-form-item label="生产线" prop="production_line">
          <el-input v-model="form.production_line" placeholder="请输入关联生产线" maxlength="50" />
        </el-form-item>
        <el-form-item label="负责人" prop="owner">
          <el-input v-model="form.owner" placeholder="请输入负责人" maxlength="50" />
        </el-form-item>
        <el-form-item label="刷新间隔" prop="refresh_interval">
          <el-input-number v-model="form.refresh_interval" :min="10" :max="3600" :step="10" style="width: 100%" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createKanbanBoard,
  deleteKanbanBoard,
  fetchKanbanBoards,
  updateKanbanBoard,
  updateKanbanBoardStatus,
} from '../api/kanbanBoards'

const router = useRouter()
const route = useRoute()

const boards = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(true)

const filters = reactive({
  boardCode: '',
  boardName: '',
  productionLine: '',
  category: '',
  status: '',
})

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const submitLoading = ref(false)
const formRef = ref(null)

const defaultForm = () => ({
  board_code: '',
  board_name: '',
  category: 'production',
  production_line: '',
  owner: '',
  refresh_interval: 60,
  description: '',
  remark: '',
})

const form = ref(defaultForm())

const formRules = {
  board_code: [{ required: true, message: '请输入看板编码', trigger: 'blur' }],
  board_name: [{ required: true, message: '请输入看板名称', trigger: 'blur' }],
  refresh_interval: [{ required: true, message: '请设置刷新间隔', trigger: 'change' }],
}

const categoryLabels = {
  production: '生产',
  quality: '品质',
  equipment: '设备',
  warehouse: '仓储',
  general: '通用',
}

const statusLabels = {
  draft: '草稿',
  active: '已发布',
  archived: '已归档',
}

function categoryLabel(category) {
  return categoryLabels[category] || category
}

function statusLabel(status) {
  return statusLabels[status] || status
}

function statusTagType(status) {
  const map = {
    draft: 'info',
    active: 'success',
    archived: 'warning',
  }
  return map[status] || 'info'
}

function resetForm() {
  form.value = defaultForm()
  editingId.value = null
  isEdit.value = false
}

function openCreateDialog() {
  resetForm()
  isEdit.value = false
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  editingId.value = row.id
  form.value = {
    board_code: row.board_code,
    board_name: row.board_name,
    category: row.category,
    production_line: row.production_line || '',
    owner: row.owner || '',
    refresh_interval: row.refresh_interval,
    description: row.description || '',
    remark: row.remark || '',
  }
  dialogVisible.value = true
}

function buildPayload() {
  const payload = {
    board_code: form.value.board_code.trim(),
    board_name: form.value.board_name.trim(),
    category: form.value.category,
    refresh_interval: form.value.refresh_interval,
  }
  if (form.value.production_line.trim()) payload.production_line = form.value.production_line.trim()
  if (form.value.owner.trim()) payload.owner = form.value.owner.trim()
  if (form.value.description.trim()) payload.description = form.value.description.trim()
  if (form.value.remark.trim()) payload.remark = form.value.remark.trim()
  return payload
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    const payload = buildPayload()
    if (isEdit.value) {
      const { board_code: _code, ...updatePayload } = payload
      await updateKanbanBoard(editingId.value, updatePayload)
      ElMessage.success('看板更新成功')
    } else {
      await createKanbanBoard(payload)
      ElMessage.success('看板创建成功')
    }
    dialogVisible.value = false
    await loadBoards()
  } catch (err) {
    if (err.message === '未登录') {
      router.push('/login')
      return
    }
    ElMessage.error(err.message || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

async function handleStatusChange(row, newStatus) {
  const actionLabels = {
    active: row.status === 'archived' ? '启用' : '发布',
    archived: '归档',
  }
  try {
    await ElMessageBox.confirm(
      `确认对看板「${row.board_name}」执行「${actionLabels[newStatus]}」操作？`,
      '状态变更确认',
      { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' },
    )
    await updateKanbanBoardStatus(row.id, newStatus)
    ElMessage.success('状态更新成功')
    await loadBoards()
  } catch (err) {
    if (err === 'cancel' || err?.message === 'cancel') return
    if (err.message === '未登录') {
      router.push('/login')
      return
    }
    ElMessage.error(err.message || '状态更新失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除看板「${row.board_name}」？此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await deleteKanbanBoard(row.id)
    ElMessage.success('删除成功')
    if (boards.value.length === 1 && page.value > 1) {
      page.value -= 1
    }
    await loadBoards()
  } catch (err) {
    if (err === 'cancel' || err?.message === 'cancel') return
    if (err.message === '未登录') {
      router.push('/login')
      return
    }
    ElMessage.error(err.message || '删除失败')
  }
}

function handleSearch() {
  page.value = 1
  loadBoards()
}

function handleReset() {
  filters.boardCode = ''
  filters.boardName = ''
  filters.productionLine = ''
  filters.category = ''
  filters.status = ''
  page.value = 1
  loadBoards()
}

async function loadBoards() {
  loading.value = true
  try {
    const data = await fetchKanbanBoards({
      page: page.value,
      pageSize: pageSize.value,
      status: filters.status || undefined,
      category: filters.category || undefined,
      productionLine: filters.productionLine || undefined,
      boardCode: filters.boardCode || undefined,
      boardName: filters.boardName || undefined,
    })
    boards.value = data.items
    total.value = data.total
  } catch (err) {
    if (err.message === '未登录') {
      router.push('/login')
      return
    }
    ElMessage.error(err.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadBoards()
  if (route.query.create === '1' || route.query.create === 'true') {
    openCreateDialog()
    router.replace({ path: '/kanban-boards' })
  }
})
</script>

<style scoped>
.kanban-boards-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-card,
.table-card {
  border-radius: 12px;
}

.search-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.table-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
