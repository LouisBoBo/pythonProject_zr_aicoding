<template>
  <div class="inspection-plans">
    <div class="plans-toolbar">
      <div class="toolbar-left">
        <h2 class="page-title">点检计划管理</h2>
        <span class="page-sub">配置设备点检频次与检查项模板</span>
      </div>
      <el-button type="primary" @click="openCreate">新增计划</el-button>
    </div>

    <div class="filter-row">
      <el-input v-model="filters.name" placeholder="计划名称" clearable style="width: 200px" @keyup.enter="loadPlans" />
      <el-select v-model="filters.isActive" placeholder="状态" clearable style="width: 120px">
        <el-option label="启用" :value="true" />
        <el-option label="停用" :value="false" />
      </el-select>
      <el-button @click="loadPlans">查询</el-button>
    </div>

    <el-table v-loading="loading" :data="plans" border stripe>
      <el-table-column prop="name" label="计划名称" min-width="140" />
      <el-table-column label="适用对象" min-width="160">
        <template #default="{ row }">
          <span v-if="row.device_name">{{ row.device_name }}</span>
          <span v-else-if="row.device_type_name">{{ row.device_type_name }}（类型）</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="检查频次" width="120">
        <template #default="{ row }">{{ frequencyLabel(row) }}</template>
      </el-table-column>
      <el-table-column label="最近执行" width="160">
        <template #default="{ row }">
          {{ row.last_executed_at ? formatDate(row.last_executed_at) : '暂无' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-switch
            :model-value="row.is_active"
            inline-prompt
            active-text="启"
            inactive-text="停"
            @change="handleToggle(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
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

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑点检计划' : '新增点检计划'"
      width="720px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px">
        <el-form-item label="计划名称" prop="name">
          <el-input v-model="form.name" maxlength="100" />
        </el-form-item>
        <el-form-item label="适用设备类型">
          <el-select v-model="form.device_type_id" clearable placeholder="按类型" style="width: 100%">
            <el-option v-for="t in deviceTypes" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="适用具体设备">
          <el-select
            v-model="form.device_id"
            filterable
            clearable
            placeholder="可选，优先于类型"
            style="width: 100%"
          >
            <el-option
              v-for="d in allDevices"
              :key="d.id"
              :label="`${d.code} · ${d.name}`"
              :value="d.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="检查频次" prop="frequency_type">
          <el-select v-model="form.frequency_type" style="width: 140px">
            <el-option label="每天" value="daily" />
            <el-option label="每周" value="weekly" />
            <el-option label="每月" value="monthly" />
            <el-option label="自定义Cron" value="custom" />
          </el-select>
          <el-input
            v-if="form.frequency_type === 'weekly'"
            v-model.number="form.frequency_value"
            placeholder="每N周"
            style="width: 100px; margin-left: 8px"
          />
          <el-input
            v-if="form.frequency_type === 'custom'"
            v-model="form.cron_expr"
            placeholder="Cron 表达式"
            style="width: 200px; margin-left: 8px"
          />
        </el-form-item>
        <el-form-item label="检查项模板">
          <div class="items-editor">
            <div v-for="(item, idx) in form.items" :key="idx" class="item-row">
              <el-input v-model="item.item_name" placeholder="项目名称" style="flex: 1" />
              <el-input v-model="item.standard_value" placeholder="标准值" style="width: 100px" />
              <el-select v-model="item.judge_type" style="width: 100px">
                <el-option label="OK/NG" value="ok_ng" />
                <el-option label="数值" value="numeric" />
              </el-select>
              <el-button :icon="Delete" circle size="small" @click="removeItem(idx)" />
            </div>
            <el-button type="primary" link @click="addItem">+ 添加检查项</el-button>
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
import { onMounted, reactive, ref } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchDevices } from '../../api/devices'
import {
  createInspectionPlan,
  deleteInspectionPlan,
  fetchInspectionPlans,
  toggleInspectionPlan,
  updateInspectionPlan,
} from '../../api/inspection'

const loading = ref(false)
const saving = ref(false)
const plans = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const allDevices = ref([])
const deviceTypes = ref([])

const filters = reactive({ name: '', isActive: null })

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const defaultForm = () => ({
  name: '',
  device_type_id: null,
  device_id: null,
  frequency_type: 'daily',
  frequency_value: null,
  cron_expr: '',
  is_active: true,
  items: [{ item_name: '', standard_value: '', judge_type: 'ok_ng', sort_order: 0 }],
})

const form = reactive(defaultForm())

const formRules = {
  name: [{ required: true, message: '请输入计划名称', trigger: 'blur' }],
  frequency_type: [{ required: true, message: '请选择频次', trigger: 'change' }],
}

function frequencyLabel(row) {
  const map = { daily: '每天', weekly: '每周', monthly: '每月', custom: '自定义' }
  let label = map[row.frequency_type] || row.frequency_type
  if (row.frequency_type === 'weekly' && row.frequency_value) {
    label += `（每${row.frequency_value}周）`
  }
  if (row.frequency_type === 'custom' && row.cron_expr) {
    label += ` ${row.cron_expr}`
  }
  return label
}

function formatDate(dt) {
  return dt.replace('T', ' ').slice(0, 16)
}

async function loadPlans() {
  loading.value = true
  try {
    const data = await fetchInspectionPlans({
      page: page.value,
      pageSize: pageSize.value,
      name: filters.name || undefined,
      isActive: filters.isActive,
    })
    plans.value = data.items
    total.value = data.total
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    device_type_id: row.device_type_id,
    device_id: row.device_id,
    frequency_type: row.frequency_type,
    frequency_value: row.frequency_value,
    cron_expr: row.cron_expr || '',
    is_active: row.is_active,
    items: row.items.length
      ? row.items.map((i) => ({
          item_name: i.item_name,
          standard_value: i.standard_value || '',
          judge_type: i.judge_type,
          sort_order: i.sort_order,
        }))
      : [{ item_name: '', standard_value: '', judge_type: 'ok_ng', sort_order: 0 }],
  })
  dialogVisible.value = true
}

function resetForm() {
  Object.assign(form, defaultForm())
}

function addItem() {
  form.items.push({ item_name: '', standard_value: '', judge_type: 'ok_ng', sort_order: form.items.length })
}

function removeItem(idx) {
  form.items.splice(idx, 1)
}

async function handleSave() {
  await formRef.value?.validate()
  if (!form.items.some((i) => i.item_name.trim())) {
    ElMessage.warning('请至少添加一个检查项')
    return
  }
  saving.value = true
  const payload = {
    name: form.name,
    device_type_id: form.device_type_id || null,
    device_id: form.device_id || null,
    frequency_type: form.frequency_type,
    frequency_value: form.frequency_value || null,
    cron_expr: form.cron_expr || null,
    is_active: form.is_active,
    items: form.items
      .filter((i) => i.item_name.trim())
      .map((i, idx) => ({
        item_name: i.item_name,
        standard_value: i.standard_value || null,
        judge_type: i.judge_type,
        sort_order: idx,
      })),
  }
  try {
    if (isEdit.value) {
      await updateInspectionPlan(editingId.value, payload)
      ElMessage.success('计划已更新')
    } else {
      await createInspectionPlan(payload)
      ElMessage.success('计划已创建')
    }
    dialogVisible.value = false
    loadPlans()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

async function handleToggle(row) {
  try {
    await toggleInspectionPlan(row.id)
    loadPlans()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除计划「${row.name}」？`, '确认')
    await deleteInspectionPlan(row.id)
    ElMessage.success('已删除')
    loadPlans()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.message || '删除失败')
  }
}

onMounted(async () => {
  loadPlans()
  try {
    const data = await fetchDevices({ pageSize: 100 })
    allDevices.value = data.items
    const typeMap = new Map()
    data.items.forEach((d) => {
      if (d.device_type_id && d.device_type_name) {
        typeMap.set(d.device_type_id, { id: d.device_type_id, name: d.device_type_name })
      }
    })
    deviceTypes.value = [...typeMap.values()]
  } catch {
    /* ignore */
  }
})
</script>

<style scoped>
.inspection-plans {
  max-width: 1100px;
}

.plans-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid #303133;
}

.page-title {
  margin: 0;
  font-size: 20px;
  color: #303133;
  font-weight: 600;
}

.page-sub {
  display: block;
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.filter-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.items-editor {
  width: 100%;
}

.item-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
</style>
