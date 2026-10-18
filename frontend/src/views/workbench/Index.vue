<template>
  <div class="workbench-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">工作台</h1>
        <p class="page-sub">逾期 · 消息 · 品质 · 库存一览，待办可直接处理</p>
      </div>
      <el-button :loading="loading" @click="loadData">刷新</el-button>
    </header>

    <el-alert
      v-if="loadError"
      class="error-alert"
      type="error"
      show-icon
      :closable="false"
      :title="loadError"
    />

    <section class="card-grid">
      <button
        v-for="card in cards"
        :key="card.key"
        type="button"
        class="summary-card"
        @click="go(card.link)"
      >
        <span class="card-label">{{ card.label }}</span>
        <span class="card-value" :class="{ warn: card.value > 0 }">
          {{ card.value }}
          <small>{{ card.unit }}</small>
        </span>
        <span class="card-hint">点击查看详情</span>
      </button>
    </section>

    <el-card shadow="never" class="todo-card">
      <div class="todo-toolbar">
        <div class="todo-title-wrap">
          <span class="todo-title">我的待办</span>
          <el-tag size="small" type="info">仅未完成</el-tag>
        </div>
        <el-select
          v-model="todoType"
          placeholder="全部类型"
          clearable
          style="width: 140px"
          @change="loadData"
        >
          <el-option label="工单" value="work_order" />
          <el-option label="库存" value="inventory" />
          <el-option label="设备" value="equipment" />
          <el-option label="品质" value="quality" />
          <el-option label="生产" value="production" />
        </el-select>
      </div>

      <el-table v-loading="loading" :data="todos" stripe border style="width: 100%">
        <el-table-column prop="priority" label="优先级" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="light" :type="priorityType(row.priority)">
              {{ priorityLabel(row.priority) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="100" align="center">
          <template #default="{ row }">{{ typeLabel(row.type) }}</template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.link"
              link
              type="primary"
              size="small"
              @click="go(row.link)"
            >
              打开
            </el-button>
            <el-button
              link
              type="success"
              size="small"
              :loading="completingId === row.id"
              @click="handleComplete(row)"
            >
              完成
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无待办" />
        </template>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { completeWorkbenchTodo, fetchWorkbench } from '../../api/dashboard'

const router = useRouter()
const loading = ref(false)
const loadError = ref('')
const cards = ref([])
const todos = ref([])
const todoType = ref('')
const completingId = ref(null)

function priorityLabel(p) {
  return { high: '高', medium: '中', low: '低' }[p] || p || '—'
}

function priorityType(p) {
  if (p === 'high') return 'danger'
  if (p === 'medium') return 'warning'
  return 'info'
}

function typeLabel(t) {
  return (
    {
      work_order: '工单',
      inventory: '库存',
      equipment: '设备',
      quality: '品质',
      production: '生产',
    }[t] || t || '—'
  )
}

function go(path) {
  if (!path) return
  router.push(path)
}

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await fetchWorkbench({
      todoType: todoType.value || undefined,
    })
    cards.value = data.cards || []
    todos.value = data.todos || []
  } catch (err) {
    cards.value = []
    todos.value = []
    loadError.value = err.message || '加载工作台失败'
  } finally {
    loading.value = false
  }
}

async function handleComplete(row) {
  try {
    await ElMessageBox.confirm(`确认完成「${row.title}」？`, '完成待办', {
      type: 'success',
    })
  } catch {
    return
  }
  completingId.value = row.id
  try {
    await completeWorkbenchTodo(row.id)
    ElMessage.success('已完成')
    await loadData()
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  } finally {
    completingId.value = null
  }
}

onMounted(loadData)
</script>

<style scoped>
.workbench-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
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

.error-alert {
  border-radius: 8px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  padding: 16px 18px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.summary-card:hover {
  border-color: #93c5fd;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.08);
}

.card-label {
  font-size: 13px;
  color: #6b7280;
}

.card-value {
  font-size: 28px;
  font-weight: 700;
  color: #111827;
  line-height: 1.1;
}

.card-value.warn {
  color: #b45309;
}

.card-value small {
  margin-left: 4px;
  font-size: 13px;
  font-weight: 500;
  color: #9ca3af;
}

.card-hint {
  font-size: 12px;
  color: #9ca3af;
}

.todo-card {
  border-radius: 10px;
  border: 1px solid #e8ecf2;
}

.todo-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.todo-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.todo-title {
  font-size: 15px;
  font-weight: 600;
  color: #374151;
}

@media (max-width: 960px) {
  .card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
