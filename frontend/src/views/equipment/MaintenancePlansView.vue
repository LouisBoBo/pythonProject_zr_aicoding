<template>
  <div class="maint-plans">
    <!-- 周期轴页首：琥珀色保养主题，区别于台账蓝灰条 -->
    <header class="plans-hero">
      <div class="hero-main">
        <div class="hero-icon">
          <el-icon><Calendar /></el-icon>
        </div>
        <div>
          <h1 class="hero-title">保养计划</h1>
          <p class="hero-desc">按设备设定周期与保养项目标准，到期自动生成工单</p>
        </div>
      </div>
      <div class="cycle-strip">
        <div class="cycle-node">
          <span class="node-num">{{ stats.enabled }}</span>
          <span class="node-label">启用计划</span>
        </div>
        <div class="cycle-line" />
        <div class="cycle-node warn">
          <span class="node-num">{{ stats.dueSoon }}</span>
          <span class="node-label">即将到期</span>
        </div>
        <div class="cycle-line" />
        <div class="cycle-node danger">
          <span class="node-num">{{ stats.overdue }}</span>
          <span class="node-label">已超期</span>
        </div>
      </div>
    </header>

    <div class="toolbar">
      <el-input
        v-model="filters.search"
        placeholder="计划名称 / 设备"
        clearable
        style="width: 220px"
        @keyup.enter="handleSearch"
      />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 110px">
        <el-option label="启用" value="enabled" />
        <el-option label="停用" value="disabled" />
      </el-select>
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
      <div class="toolbar-spacer" />
      <el-button type="primary" :icon="Plus" @click="openCreate">新增计划</el-button>
    </div>

    <div class="table-wrap">
      <el-table
        v-loading="loading"
        :data="items"
        border
        :row-class-name="rowClassName"
      >
        <el-table-column prop="name" label="计划名称" min-width="140" />
        <el-table-column label="关联设备" min-width="160">
          <template #default="{ row }">
            <span class="eq-ref">{{ row.equipment_code }}</span>
            <span class="eq-name">{{ row.equipment_name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="保养周期" width="120">
          <template #default="{ row }">{{ cycleLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="项目数" width="80" align="center">
          <template #default="{ row }">{{ row.items?.length || 0 }}</template>
        </el-table-column>
        <el-table-column label="下次到期" width="120">
          <template #default="{ row }">
            {{ formatDate(row.next_due_at) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="row.status === 'enabled'"
              inline-prompt
              active-text="启"
              inactive-text="停"
              @change="handleToggle(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button
              link
              type="primary"
              size="small"
              :disabled="row.status !== 'enabled'"
              @click="handleGenerate(row)"
            >
              生成工单
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
          :page-sizes="[10, 20]"
          layout="total, prev, pager, next"
          background
          @change="loadPlans"
        />
      </div>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑保养计划' : '新增保养计划'"
      width="720px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px">
        <el-form-item label="关联设备" prop="equipment_id">
          <el-select
            v-model="form.equipment_id"
            filterable
            placeholder="选择设备"
            style="width: 100%"
          >
            <el-option
              v-for="eq in equipmentOptions"
              :key="eq.id"
              :label="`${eq.equipment_code} · ${eq.name}`"
              :value="eq.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="计划名称" prop="name">
          <el-input v-model="form.name" maxlength="100" />
        </el-form-item>
        <el-form-item label="保养周期" required>
          <el-select v-model="form.cycle_type" style="width: 120px">
            <el-option label="按天" value="day" />
            <el-option label="按周" value="week" />
            <el-option label="按月" value="month" />
            <el-option label="运行时长" value="runtime" />
          </el-select>
          <span class="cycle-sep">每</span>
          <el-input-number v-model="form.cycle_value" :min="1" :max="365" />
          <span class="cycle-unit">{{ cycleUnitLabel }}</span>
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="enabled">启用</el-radio>
            <el-radio value="disabled">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="保养项目">
          <div class="items-editor">
            <div v-for="(item, idx) in form.items" :key="idx" class="item-row">
              <el-input v-model="item.item_name" placeholder="项目名称" style="flex: 1" />
              <el-input v-model="item.check_method" placeholder="检查方法" style="flex: 1" />
              <el-input v-model="item.standard" placeholder="合格标准" style="flex: 1" />
              <el-button :icon="Delete" circle size="small" @click="removeItem(idx)" />
            </div>
            <el-button type="primary" link @click="addItem">+ 添加保养项</el-button>
          </div>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { Calendar, Delete, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchEquipmentList } from '../../api/equipment'
import {
  createMaintenancePlan,
  deleteMaintenancePlan,
  fetchMaintenanceAlerts,
  fetchMaintenancePlans,
  generateOrderFromPlan,
  updateMaintenancePlan,
} from '../../api/equipmentMaintenance'

const loading = ref(false)
const saving = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const formRef = ref(null)
const equipmentOptions = ref([])

const stats = reactive({ enabled: 0, dueSoon: 0, overdue: 0 })

const filters = reactive({ search: '', status: '' })

const form = reactive({
  equipment_id: null,
  name: '',
  cycle_type: 'month',
  cycle_value: 1,
  status: 'enabled',
  items: [{ item_name: '', check_method: '', standard: '' }],
})

const formRules = {
  equipment_id: [{ required: true, message: '请选择设备', trigger: 'change' }],
  name: [{ required: true, message: '请输入计划名称', trigger: 'blur' }],
}

const cycleUnitLabel = computed(() => {
  const map = { day: '天', week: '周', month: '月', runtime: '运行小时' }
  return map[form.cycle_type] || ''
})

function cycleLabel(row) {
  const typeMap = { day: '天', week: '周', month: '月', runtime: '运行时长' }
  return `每 ${row.cycle_value} ${typeMap[row.cycle_type] || row.cycle_type}`
}

function formatDate(val) {
  if (!val) return '-'
  const d = new Date(val)
  if (Number.isNaN(d.getTime())) return val
  return d.toLocaleDateString('zh-CN')
}

function rowClassName({ row }) {
  if (row.status !== 'enabled') return ''
  if (row.alert_level === 'overdue') return 'row-overdue'
  if (row.alert_level === 'due_soon') return 'row-due-soon'
  return ''
}

async function loadStats() {
  try {
    const alerts = await fetchMaintenanceAlerts()
    stats.dueSoon = alerts.due_soon.filter((a) => a.type === 'plan').length
    stats.overdue = alerts.overdue.filter((a) => a.type === 'plan').length
  } catch {
    /* ignore */
  }
}

async function loadPlans() {
  loading.value = true
  try {
    const res = await fetchMaintenancePlans({
      page: page.value,
      pageSize: pageSize.value,
      search: filters.search || undefined,
      status: filters.status || undefined,
    })
    items.value = res.items
    total.value = res.total
    stats.enabled = res.items.filter((p) => p.status === 'enabled').length
    await loadStats()
  } catch (err) {
    ElMessage.error(err.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function loadEquipmentOptions() {
  try {
    const res = await fetchEquipmentList({ page: 1, pageSize: 100 })
    equipmentOptions.value = res.items
  } catch {
    equipmentOptions.value = []
  }
}

function handleSearch() {
  page.value = 1
  loadPlans()
}

function handleReset() {
  filters.search = ''
  filters.status = ''
  handleSearch()
}

function resetForm() {
  Object.assign(form, {
    equipment_id: null,
    name: '',
    cycle_type: 'month',
    cycle_value: 1,
    status: 'enabled',
    items: [{ item_name: '', check_method: '', standard: '' }],
  })
  editId.value = null
  isEdit.value = false
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    equipment_id: row.equipment_id,
    name: row.name,
    cycle_type: row.cycle_type,
    cycle_value: row.cycle_value,
    status: row.status,
    items: row.items?.length
      ? row.items.map((i) => ({ ...i }))
      : [{ item_name: '', check_method: '', standard: '' }],
  })
  dialogVisible.value = true
}

function addItem() {
  form.items.push({ item_name: '', check_method: '', standard: '' })
}

function removeItem(idx) {
  if (form.items.length > 1) form.items.splice(idx, 1)
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  const validItems = form.items.filter((i) => i.item_name?.trim())
  if (!validItems.length) {
    ElMessage.warning('请至少添加一项保养项目')
    return
  }

  saving.value = true
  const payload = {
    equipment_id: form.equipment_id,
    name: form.name,
    cycle_type: form.cycle_type,
    cycle_value: form.cycle_value,
    status: form.status,
    items: validItems,
  }
  try {
    if (isEdit.value) {
      await updateMaintenancePlan(editId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await createMaintenancePlan(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadPlans()
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除计划「${row.name}」？`, '确认', { type: 'warning' })
    await deleteMaintenancePlan(row.id)
    ElMessage.success('已删除')
    loadPlans()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.message || '删除失败')
  }
}

async function handleGenerate(row) {
  try {
    await generateOrderFromPlan(row.id)
    ElMessage.success('保养工单已生成')
  } catch (err) {
    ElMessage.error(err.message || '生成失败')
  }
}

async function handleToggle(row) {
  const nextStatus = row.status === 'enabled' ? 'disabled' : 'enabled'
  try {
    await updateMaintenancePlan(row.id, { status: nextStatus })
    ElMessage.success(nextStatus === 'enabled' ? '计划已启用' : '计划已停用')
    loadPlans()
  } catch (err) {
    ElMessage.error(err.message || '状态更新失败')
  }
}

onMounted(() => {
  loadEquipmentOptions()
  loadPlans()
})
</script>

<style scoped>
.maint-plans {
  min-height: 100%;
  background: #f4f2ed;
}

.plans-hero {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 24px;
  background: linear-gradient(120deg, #4a4035 0%, #5c5044 55%, #3d5248 100%);
  border-radius: 4px;
  margin-bottom: 14px;
}

.hero-main {
  display: flex;
  align-items: center;
  gap: 16px;
}

.hero-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(212, 165, 90, 0.2);
  border: 1px solid rgba(212, 165, 90, 0.45);
  border-radius: 4px;
  color: #d4a55a;
  font-size: 24px;
}

.hero-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #f5efe6;
}

.hero-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: rgba(245, 239, 230, 0.6);
}

.cycle-strip {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.15);
  border-radius: 4px;
}

.cycle-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 72px;
}

.node-num {
  font-size: 22px;
  font-weight: 700;
  color: #d4a55a;
  line-height: 1.2;
}

.cycle-node.warn .node-num {
  color: #e6b84d;
}

.cycle-node.danger .node-num {
  color: #e07070;
}

.node-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.55);
  margin-top: 2px;
}

.cycle-line {
  width: 32px;
  height: 2px;
  background: rgba(212, 165, 90, 0.35);
  margin: 0 8px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #e0dcd4;
  border-radius: 4px;
  margin-bottom: 12px;
}

.toolbar-spacer {
  flex: 1;
}

.table-wrap {
  background: #fff;
  border: 1px solid #e0dcd4;
  border-radius: 4px;
  padding: 12px;
}

.eq-ref {
  display: block;
  font-family: monospace;
  font-size: 12px;
  color: #8b7355;
}

.eq-name {
  font-size: 13px;
  color: #334155;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.items-editor {
  width: 100%;
}

.item-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}

.cycle-sep,
.cycle-unit {
  margin: 0 8px;
  color: #64748b;
  font-size: 13px;
}

:deep(.row-due-soon) {
  background-color: #fffbeb !important;
}

:deep(.row-overdue) {
  background-color: #fef2f2 !important;
}
</style>
