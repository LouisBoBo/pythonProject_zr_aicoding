<template>
  <div class="maint-orders">
    <!-- 工单流转条：横向状态管道，区别于计划页周期轴 -->
    <header class="orders-hero">
      <div class="hero-left">
        <div class="hero-badge">
          <el-icon><Tools /></el-icon>
        </div>
        <div>
          <h1 class="hero-title">保养工单</h1>
          <p class="hero-desc">派工执行 · 逐项记录保养结果</p>
        </div>
      </div>
      <div class="status-pipeline">
        <div
          v-for="(step, idx) in pipelineSteps"
          :key="step.key"
          class="pipe-step"
          :class="{ active: statusFilter === step.key }"
          @click="filterByStatus(step.key)"
        >
          <span class="pipe-count">{{ step.count }}</span>
          <span class="pipe-label">{{ step.label }}</span>
          <span v-if="idx < pipelineSteps.length - 1" class="pipe-arrow">→</span>
        </div>
      </div>
    </header>

    <div class="toolbar">
      <el-input
        v-model="filters.search"
        placeholder="工单号 / 设备"
        clearable
        style="width: 200px"
        @keyup.enter="handleSearch"
      />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px">
        <el-option label="待执行" value="pending" />
        <el-option label="执行中" value="in_progress" />
        <el-option label="已完成" value="completed" />
        <el-option label="已关闭" value="closed" />
      </el-select>
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
    </div>

    <div class="table-wrap">
      <el-table
        v-loading="loading"
        :data="items"
        border
        :row-class-name="rowClassName"
      >
        <el-table-column prop="order_no" label="工单号" min-width="150" fixed="left">
          <template #default="{ row }">
            <span class="order-no">{{ row.order_no }}</span>
          </template>
        </el-table-column>
        <el-table-column label="设备" min-width="150">
          <template #default="{ row }">
            {{ row.equipment_code }} · {{ row.equipment_name }}
          </template>
        </el-table-column>
        <el-table-column label="关联计划" min-width="120">
          <template #default="{ row }">{{ row.plan_name || '手动创建' }}</template>
        </el-table-column>
        <el-table-column label="计划开始" width="110">
          <template #default="{ row }">{{ formatDate(row.planned_start_at) }}</template>
        </el-table-column>
        <el-table-column label="指派人" width="90">
          <template #default="{ row }">{{ row.assignee || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span class="order-status" :class="'os-' + row.status">
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending'"
              link
              type="primary"
              size="small"
              @click="openDispatch(row)"
            >
              派工
            </el-button>
            <el-button
              v-if="row.status === 'pending'"
              link
              type="primary"
              size="small"
              @click="handleStart(row)"
            >
              开始
            </el-button>
            <el-button
              v-if="row.status === 'pending' || row.status === 'in_progress'"
              link
              type="primary"
              size="small"
              @click="openExecute(row)"
            >
              执行记录
            </el-button>
            <el-button
              v-if="row.status === 'pending'"
              link
              type="danger"
              size="small"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20]"
          layout="total, prev, pager, next"
          background
          @change="loadOrders"
        />
      </div>
    </div>

    <!-- 派工弹窗 -->
    <el-dialog v-model="dispatchVisible" title="派工" width="480px" destroy-on-close>
      <el-form ref="dispatchRef" :model="dispatchForm" :rules="dispatchRules" label-width="90px">
        <el-form-item label="指派人" prop="assignee">
          <el-input v-model="dispatchForm.assignee" maxlength="50" />
        </el-form-item>
        <el-form-item label="计划开始">
          <el-date-picker
            v-model="dispatchForm.planned_start_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dispatchVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleDispatch">确认派工</el-button>
      </template>
    </el-dialog>

    <!-- 执行记录弹窗 -->
    <el-dialog
      v-model="executeVisible"
      title="保养执行记录"
      width="760px"
      destroy-on-close
      @closed="resetExecuteForm"
    >
      <div v-if="currentOrder" class="execute-header">
        <span>{{ currentOrder.order_no }}</span>
        <span>{{ currentOrder.equipment_name }}</span>
      </div>
      <el-form ref="executeRef" :model="executeForm" :rules="executeRules" label-width="80px">
        <el-form-item label="执行人" prop="executor">
          <el-input v-model="executeForm.executor" maxlength="50" style="width: 200px" />
        </el-form-item>
        <el-form-item label="保养项">
          <el-table :data="executeForm.results" border size="small">
            <el-table-column prop="item_name" label="项目" min-width="100" />
            <el-table-column prop="check_method" label="检查方法" min-width="100">
              <template #default="{ row }">{{ row.check_method || '-' }}</template>
            </el-table-column>
            <el-table-column prop="standard" label="合格标准" min-width="100">
              <template #default="{ row }">{{ row.standard || '-' }}</template>
            </el-table-column>
            <el-table-column label="执行结果" min-width="120">
              <template #default="{ row }">
                <el-input v-model="row.result" placeholder="填写结果" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="备注" min-width="100">
              <template #default="{ row }">
                <el-input v-model="row.remark" placeholder="备注" size="small" />
              </template>
            </el-table-column>
          </el-table>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="executeForm.remark" type="textarea" :rows="2" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="executeVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleExecute">提交完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Tools } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteMaintenanceOrder,
  dispatchMaintenanceOrder,
  executeMaintenanceOrder,
  fetchMaintenanceOrder,
  fetchMaintenancePlan,
  fetchMaintenanceOrders,
  startMaintenanceOrder,
} from '../../api/equipmentMaintenance'

const loading = ref(false)
const submitting = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const statusFilter = ref('')

const filters = reactive({ search: '', status: '' })

const statusCounts = reactive({
  pending: 0,
  in_progress: 0,
  completed: 0,
  closed: 0,
})

const pipelineSteps = computed(() => [
  { key: 'pending', label: '待执行', count: statusCounts.pending },
  { key: 'in_progress', label: '执行中', count: statusCounts.in_progress },
  { key: 'completed', label: '已完成', count: statusCounts.completed },
  { key: 'closed', label: '已关闭', count: statusCounts.closed },
])

const dispatchVisible = ref(false)
const executeVisible = ref(false)
const currentOrder = ref(null)
const dispatchRef = ref(null)
const executeRef = ref(null)

const dispatchForm = reactive({ assignee: '', planned_start_at: null })
const dispatchRules = {
  assignee: [{ required: true, message: '请输入指派人', trigger: 'blur' }],
}

const executeForm = reactive({
  executor: '',
  results: [],
  remark: '',
})
const executeRules = {
  executor: [{ required: true, message: '请输入执行人', trigger: 'blur' }],
}

function statusLabel(s) {
  const map = {
    pending: '待执行',
    in_progress: '执行中',
    completed: '已完成',
    closed: '已关闭',
  }
  return map[s] || s
}

function formatDate(val) {
  if (!val) return '-'
  const d = new Date(val)
  if (Number.isNaN(d.getTime())) return val
  return d.toLocaleDateString('zh-CN')
}

function rowClassName({ row }) {
  if (!['pending', 'in_progress'].includes(row.status)) return ''
  if (row.alert_level === 'overdue') return 'row-overdue'
  if (row.alert_level === 'due_soon') return 'row-due-soon'
  return ''
}

async function loadStatusCounts() {
  try {
    for (const s of ['pending', 'in_progress', 'completed', 'closed']) {
      const res = await fetchMaintenanceOrders({ page: 1, pageSize: 1, status: s })
      statusCounts[s] = res.total
    }
  } catch {
    /* ignore */
  }
}

async function loadOrders() {
  loading.value = true
  try {
    const res = await fetchMaintenanceOrders({
      page: page.value,
      pageSize: pageSize.value,
      search: filters.search || undefined,
      status: filters.status || undefined,
    })
    items.value = res.items
    total.value = res.total
    await loadStatusCounts()
  } catch (err) {
    ElMessage.error(err.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadOrders()
}

function handleReset() {
  filters.search = ''
  filters.status = ''
  statusFilter.value = ''
  handleSearch()
}

function filterByStatus(key) {
  statusFilter.value = key
  filters.status = key
  handleSearch()
}

function openDispatch(row) {
  currentOrder.value = row
  dispatchForm.assignee = row.assignee || ''
  dispatchForm.planned_start_at = row.planned_start_at || null
  dispatchVisible.value = true
}

async function handleDispatch() {
  const valid = await dispatchRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await dispatchMaintenanceOrder(currentOrder.value.id, {
      assignee: dispatchForm.assignee,
      planned_start_at: dispatchForm.planned_start_at || undefined,
    })
    ElMessage.success('派工成功')
    dispatchVisible.value = false
    loadOrders()
  } catch (err) {
    ElMessage.error(err.message || '派工失败')
  } finally {
    submitting.value = false
  }
}

async function handleStart(row) {
  try {
    await startMaintenanceOrder(row.id)
    ElMessage.success('已开始执行')
    loadOrders()
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  }
}

async function openExecute(row) {
  currentOrder.value = row
  try {
    const detail = await fetchMaintenanceOrder(row.id)
    let items = []
    if (detail.results?.length) {
      items = detail.results.map((i) => ({
        item_name: i.item_name,
        check_method: i.check_method || '',
        standard: i.standard || '',
        result: i.result || '',
        remark: i.remark || '',
      }))
    } else if (detail.plan_id) {
      const plan = await fetchMaintenancePlan(detail.plan_id)
      items = (plan.items || []).map((i) => ({
        item_name: i.item_name,
        check_method: i.check_method || '',
        standard: i.standard || '',
        result: '',
        remark: '',
      }))
    }
    if (!items.length) {
      items = [{ item_name: '保养检查', check_method: '', standard: '', result: '', remark: '' }]
    }
    executeForm.executor = detail.executor || detail.assignee || ''
    executeForm.results = items
    executeForm.remark = detail.remark || ''
    executeVisible.value = true
  } catch (err) {
    ElMessage.error(err.message || '加载失败')
  }
}

function resetExecuteForm() {
  executeForm.executor = ''
  executeForm.results = []
  executeForm.remark = ''
  currentOrder.value = null
}

async function handleExecute() {
  const valid = await executeRef.value?.validate().catch(() => false)
  if (!valid) return
  const filled = executeForm.results.filter((r) => r.result?.trim())
  if (!filled.length) {
    ElMessage.warning('请至少填写一项执行结果')
    return
  }
  submitting.value = true
  try {
    await executeMaintenanceOrder(currentOrder.value.id, {
      executor: executeForm.executor,
      results: filled,
      remark: executeForm.remark || null,
    })
    ElMessage.success('保养记录已提交')
    executeVisible.value = false
    loadOrders()
  } catch (err) {
    ElMessage.error(err.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除工单 ${row.order_no}？`, '确认', { type: 'warning' })
    await deleteMaintenanceOrder(row.id)
    ElMessage.success('已删除')
    loadOrders()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.message || '删除失败')
  }
}

onMounted(loadOrders)
</script>

<style scoped>
.maint-orders {
  min-height: 100%;
  background: #eef0f3;
}

.orders-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 22px;
  background: #2c3540;
  border-left: 4px solid #5b9bd5;
  border-radius: 4px;
  margin-bottom: 14px;
}

.hero-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.hero-badge {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(91, 155, 213, 0.15);
  border: 1px solid rgba(91, 155, 213, 0.4);
  border-radius: 4px;
  color: #5b9bd5;
  font-size: 22px;
}

.hero-title {
  margin: 0;
  font-size: 19px;
  font-weight: 600;
  color: #e8ecf0;
}

.hero-desc {
  margin: 3px 0 0;
  font-size: 12px;
  color: rgba(232, 236, 240, 0.55);
}

.status-pipeline {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pipe-step {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.15s;
}

.pipe-step:hover,
.pipe-step.active {
  background: rgba(91, 155, 213, 0.12);
}

.pipe-count {
  font-size: 20px;
  font-weight: 700;
  color: #5b9bd5;
}

.pipe-label {
  font-size: 12px;
  color: rgba(232, 236, 240, 0.7);
}

.pipe-arrow {
  margin-left: 8px;
  color: rgba(232, 236, 240, 0.3);
  font-size: 14px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #d8dde3;
  border-radius: 4px;
  margin-bottom: 12px;
}

.table-wrap {
  background: #fff;
  border: 1px solid #d8dde3;
  border-radius: 4px;
  padding: 12px;
}

.order-no {
  font-family: monospace;
  font-size: 13px;
  color: #2c5282;
}

.order-status {
  display: inline-block;
  padding: 2px 8px;
  font-size: 12px;
  border-radius: 2px;
}

.os-pending {
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fcd34d;
}

.os-in_progress {
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #93c5fd;
}

.os-completed {
  color: #15803d;
  background: #f0fdf4;
  border: 1px solid #86efac;
}

.os-closed {
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.execute-header {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  padding: 10px 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 13px;
  color: #475569;
}

:deep(.row-due-soon) {
  background-color: #fffbeb !important;
}

:deep(.row-overdue) {
  background-color: #fef2f2 !important;
}
</style>
