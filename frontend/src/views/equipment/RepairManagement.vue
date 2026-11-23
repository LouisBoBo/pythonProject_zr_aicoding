<template>
  <div class="repair-management">
    <!-- 页首 -->
    <header class="repair-hero">
      <div class="hero-left">
        <div class="hero-badge">
          <el-icon><Tools /></el-icon>
        </div>
        <div>
          <h1 class="hero-title">维修管理</h1>
          <p class="hero-desc">故障报修 · 进度追踪 · 配件与费用汇总</p>
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

    <!-- 搜索筛选区 -->
    <div class="toolbar">
      <el-input
        v-model="filters.keyword"
        placeholder="工单号 / 设备名称 / 故障描述"
        clearable
        style="width: 280px"
        :prefix-icon="Search"
        @keyup.enter="handleSearch"
      />
      <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 130px">
        <el-option label="待处理" value="pending" />
        <el-option label="处理中" value="in_progress" />
        <el-option label="已完成" value="completed" />
        <el-option label="已关闭" value="closed" />
      </el-select>
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
      <div class="toolbar-spacer" />
      <el-button type="primary" :icon="Plus" @click="openCreateDrawer">新增维修工单</el-button>
    </div>

  <div class="pcb-fault-strip" v-if="pcbFaultPresets.length">
    <span class="pcb-fault-strip__label">PCB 产线故障（16 条）</span>
    <el-scrollbar class="pcb-fault-scroll" always>
      <div class="pcb-fault-chips">
        <button
          v-for="(item, idx) in pcbFaultPresets"
          :key="item.noSuffix + '-' + idx"
          type="button"
          class="pcb-fault-chip"
          :class="{ active: filters.keyword === item.faultDescription }"
          :title="pcbRepairOrderNo(item.noSuffix)"
          @click="filterByPcbFault(item.faultDescription)"
        >
          {{ item.faultDescription }}
        </button>
      </div>
    </el-scrollbar>
    <el-button
      v-if="filters.keyword"
      link
      type="primary"
      size="small"
      class="pcb-fault-clear"
      @click="handleReset"
    >
      清除筛选
    </el-button>
  </div>

    <!-- 表格 -->
    <div class="table-wrap">
      <el-table
        v-loading="loading"
        :data="items"
        border
        highlight-current-row
        @row-click="goDetail"
      >
        <el-table-column prop="repair_no" label="工单号" min-width="150" fixed="left">
          <template #default="{ row }">
            <span class="repair-no">{{ row.repair_no }}</span>
            <el-tag
              v-if="isPcbDemoRepairNo(row.repair_no)"
              size="small"
              type="warning"
              effect="plain"
              class="pcb-demo-tag"
            >
              PCB
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="设备名称" min-width="160">
          <template #default="{ row }">
            <div class="cell-equipment">
              <span class="equip-name">{{ row.equipment_name }}</span>
              <span class="equip-code">{{ row.equipment_code }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="fault_description" label="故障描述" min-width="220" show-overflow-tooltip />
        <el-table-column label="紧急程度" width="90" align="center">
          <template #default="{ row }">
            <span class="urgency-tag" :class="'urg-' + row.urgency">{{ urgencyLabel(row.urgency) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span class="repair-status" :class="'rs-' + row.status">{{ statusLabel(row.status) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="reporter" label="报修人" width="90" />
        <el-table-column label="报修时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="维修完成时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.repair_completed_at, true) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="warning"
              size="small"
              :loading="diagnoseLoadingId === row.id"
              :disabled="diagnoseLoadingId != null && diagnoseLoadingId !== row.id"
              @click.stop="handleAiDiagnose(row)"
            >
              AI诊断
            </el-button>
            <el-button link type="primary" size="small" @click.stop="openEditDrawer(row)">编辑</el-button>
            <el-button
              v-if="row.status === 'pending'"
              link
              type="danger"
              size="small"
              @click.stop="handleDelete(row)"
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
          :page-sizes="repairListPageSizeOptions"
          :default-page-size="repairListDefaultPageSize"
          layout="total, sizes, prev, pager, next"
          background
          @change="loadList"
        />
      </div>
    </div>

    <!-- 右侧抽屉：新增/编辑 -->
    <el-drawer
      v-model="drawerVisible"
      :title="isEdit ? '编辑维修工单' : '新增维修工单'"
      size="520px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="90px" class="repair-form">
        <el-form-item label="报修设备" prop="equipment_id">
          <el-select
            v-model="form.equipment_id"
            placeholder="选择设备"
            filterable
            style="width: 100%"
            :disabled="isEdit"
          >
            <el-option
              v-for="eq in equipmentList"
              :key="eq.id"
              :label="`${eq.equipment_code} · ${eq.name}`"
              :value="eq.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="故障分类" prop="fault_category">
          <el-select v-model="form.fault_category" style="width: 100%">
            <el-option
              v-for="cat in faultCategories"
              :key="cat"
              :label="cat"
              :value="cat"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="紧急程度" prop="urgency">
          <el-radio-group v-model="form.urgency">
            <el-radio-button value="low">低</el-radio-button>
            <el-radio-button value="normal">普通</el-radio-button>
            <el-radio-button value="high">紧急</el-radio-button>
            <el-radio-button value="urgent">特急</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="报修人" prop="reporter">
          <el-input v-model="form.reporter" maxlength="50" placeholder="报修人姓名" />
        </el-form-item>
        <el-form-item label="故障描述" prop="fault_description">
          <el-input
            v-model="form.fault_description"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            placeholder="请详细描述故障现象..."
          />
        </el-form-item>

        <!-- 编辑时显示更多字段 -->
        <template v-if="isEdit">
          <el-divider content-position="left">维修处理</el-divider>
          <el-form-item label="状态" prop="status">
            <el-select v-model="form.status" style="width: 100%">
              <el-option label="待处理" value="pending" />
              <el-option label="处理中" value="in_progress" />
              <el-option label="已完成" value="completed" />
              <el-option label="已关闭" value="closed" />
            </el-select>
          </el-form-item>
          <el-form-item label="维修人员" prop="repair_person">
            <el-input v-model="form.repair_person" maxlength="50" placeholder="指定维修人员" />
          </el-form-item>
          <el-form-item label="维修描述" prop="repair_description">
            <el-input
              v-model="form.repair_description"
              type="textarea"
              :rows="3"
              maxlength="2000"
              show-word-limit
              placeholder="维修过程与措施..."
            />
          </el-form-item>
          <el-divider content-position="left">更换配件</el-divider>
          <div class="parts-editor">
            <div v-for="(part, idx) in form.parts" :key="idx" class="part-row">
              <el-input v-model="part.part_name" placeholder="名称" size="small" style="width: 110px" />
              <el-input v-model="part.part_spec" placeholder="规格" size="small" style="width: 80px" />
              <el-input-number v-model="part.quantity" :min="1" size="small" style="width: 60px" />
              <el-input v-model="part.unit" placeholder="单位" size="small" style="width: 50px" />
              <el-input-number v-model="part.unit_price" :min="0" :precision="2" size="small" style="width: 90px" controls-position="right" />
              <el-button link type="danger" size="small" @click="removePart(idx)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <el-button link type="primary" size="small" :icon="Plus" @click="addPart">添加配件</el-button>
          </div>
        </template>

        <el-form-item label="现场图片">
          <el-upload
            list-type="picture-card"
            :auto-upload="false"
            v-model:file-list="imageFiles"
            :limit="6"
            accept="image/*"
          >
            <el-icon><Plus /></el-icon>
          </el-upload>
          <p class="upload-hint">支持 jpg/png，单张不超过 5MB（演示版暂不上传服务器）</p>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="drawerVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存修改' : '提交工单' }}
        </el-button>
      </template>
    </el-drawer>

    <!-- AI 诊断结果 -->
    <el-dialog
      v-model="diagnoseDialogVisible"
      title="AI 诊断结果"
      width="640px"
      destroy-on-close
      class="ai-diagnose-dialog"
      @closed="diagnoseHtml = ''"
    >
      <div v-if="diagnoseHtml" class="ai-diagnose-md" v-html="diagnoseHtml" />
      <el-empty v-else description="暂无诊断内容" />
      <template #footer>
        <el-button type="primary" @click="diagnoseDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Tools, Search, Plus, Delete } from '@element-plus/icons-vue'
import {
  fetchRepairs,
  fetchRepairDetail,
  createRepair,
  updateRepair,
  deleteRepair,
  REPAIR_LIST_DEFAULT_PAGE_SIZE,
  REPAIR_LIST_MAX_PAGE_SIZE,
} from '../../api/equipmentRepair'
import { requestAiDiagnose } from '../../api/equipmentAiDiagnose'
import { fetchEquipmentList } from '../../api/equipment'
import { usePermissions } from '../../composables/usePermissions'
import { renderMarkdownLite } from '../../utils/markdownLite'
import {
  PCB_EQUIPMENT_REPAIR_ORDERS,
  isPcbDemoRepairNo,
  pcbRepairOrderNo,
} from '../../config/equipmentRepairPcbOrders.js'

const router = useRouter()
const { user } = usePermissions()
const pcbFaultPresets = PCB_EQUIPMENT_REPAIR_ORDERS

// --- AI 诊断 ---
const diagnoseLoadingId = ref(null)
const diagnoseDialogVisible = ref(false)
const diagnoseHtml = ref('')

// --- 列表 ---
const loading = ref(false)
const items = ref([])
const total = ref(0)
const repairListDefaultPageSize = REPAIR_LIST_DEFAULT_PAGE_SIZE
const repairListPageSizeOptions = [10, 20, 50, REPAIR_LIST_MAX_PAGE_SIZE]

const page = ref(1)
const pageSize = ref(repairListDefaultPageSize)
const statusFilter = ref('')

const filters = reactive({ keyword: '', status: '' })

const statusCounts = reactive({
  pending: 0,
  in_progress: 0,
  completed: 0,
  closed: 0,
})

const pipelineSteps = computed(() => [
  { key: 'pending', label: '待处理', count: statusCounts.pending },
  { key: 'in_progress', label: '处理中', count: statusCounts.in_progress },
  { key: 'completed', label: '已完成', count: statusCounts.completed },
  { key: 'closed', label: '已关闭', count: statusCounts.closed },
])

const faultCategories = [
  '机械故障', '电气故障', '液压故障', '气动故障',
  '控制系统故障', '传动故障', '润滑故障', '其他',
]

// --- 抽屉 ---
const drawerVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formRef = ref(null)
const equipmentList = ref([])
const imageFiles = ref([])

const defaultForm = () => ({
  equipment_id: null,
  fault_category: '机械故障',
  urgency: 'normal',
  reporter: '',
  fault_description: '',
  status: 'pending',
  repair_person: '',
  repair_description: '',
  parts: [],
})

const form = reactive(defaultForm())

const formRules = {
  equipment_id: [{ required: true, message: '请选择设备', trigger: 'change' }],
  fault_category: [{ required: true, message: '请选择故障分类', trigger: 'change' }],
  urgency: [{ required: true, message: '请选择紧急程度', trigger: 'change' }],
  reporter: [{ required: true, message: '请输入报修人', trigger: 'blur' }],
  fault_description: [{ required: true, message: '请输入故障描述', trigger: 'blur' }],
}

// --- helpers ---
function urgencyLabel(v) {
  const m = { low: '低', normal: '普通', high: '紧急', urgent: '特急' }
  return m[v] || v
}

function statusLabel(s) {
  const m = { pending: '待处理', in_progress: '处理中', completed: '已完成', closed: '已关闭' }
  return m[s] || s
}

function formatDateTime(val, emptyDash = false) {
  if (!val) return emptyDash ? '—' : '-'
  const d = new Date(val)
  if (Number.isNaN(d.getTime())) return val
  return d.toLocaleString('zh-CN', { hour12: false })
}

// --- 加载 ---
async function loadStatusCounts() {
  try {
    for (const s of ['pending', 'in_progress', 'completed', 'closed']) {
      const res = await fetchRepairs({ page: 1, pageSize: 1, status: s })
      statusCounts[s] = res.total
    }
  } catch { /* ignore */ }
}

function clampRepairListPageSize(size) {
  const n = Number(size)
  if (!Number.isFinite(n)) return repairListDefaultPageSize
  return Math.min(REPAIR_LIST_MAX_PAGE_SIZE, Math.max(1, Math.trunc(n)))
}

async function loadList() {
  loading.value = true
  try {
    pageSize.value = clampRepairListPageSize(pageSize.value)
    const res = await fetchRepairs({
      page: page.value,
      pageSize: pageSize.value,
      keyword: filters.keyword || undefined,
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

async function loadEquipmentList() {
  try {
    const res = await fetchEquipmentList({ page: 1, pageSize: REPAIR_LIST_MAX_PAGE_SIZE })
    equipmentList.value = res.items
  } catch { /* ignore */ }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.keyword = ''
  filters.status = ''
  statusFilter.value = ''
  handleSearch()
}

function filterByStatus(key) {
  statusFilter.value = key
  filters.status = key
  handleSearch()
}

function filterByPcbFault(faultDescription) {
  filters.keyword = faultDescription
  filters.status = ''
  statusFilter.value = ''
  handleSearch()
}

// --- 明细跳转 ---
function goDetail(row) {
  router.push(`/equipment/repairs/${row.id}`)
}

// --- 新增 ---
function openCreateDrawer() {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, defaultForm())
  imageFiles.value = []
  drawerVisible.value = true
  loadEquipmentList()
}

// --- 编辑 ---
async function openEditDrawer(row) {
  isEdit.value = true
  editingId.value = row.id
  await loadEquipmentList()
  try {
    const detail = await fetchRepairDetail(row.id)
    Object.assign(form, {
      equipment_id: detail.equipment_id,
      fault_category: detail.fault_category,
      urgency: detail.urgency,
      reporter: detail.reporter,
      fault_description: detail.fault_description,
      status: detail.status,
      repair_person: detail.repair_person || '',
      repair_description: detail.repair_description || '',
      parts: (detail.parts || []).map(p => ({ ...p })),
    })
  } catch (err) {
    ElMessage.error(err.message || '加载详情失败')
    return
  }
  imageFiles.value = []
  drawerVisible.value = true
}

function resetForm() {
  Object.assign(form, defaultForm())
  formRef.value?.resetFields()
}

// --- 配件编辑 ---
function addPart() {
  form.parts.push({
    part_name: '',
    part_spec: '',
    quantity: 1,
    unit: '个',
    unit_price: 0,
  })
}

function removePart(idx) {
  form.parts.splice(idx, 1)
}

// --- 提交 ---
async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = {
      equipment_id: form.equipment_id,
      fault_category: form.fault_category,
      fault_description: form.fault_description,
      urgency: form.urgency,
      reporter: form.reporter,
    }

    if (isEdit.value) {
      payload.status = form.status
      payload.repair_person = form.repair_person || null
      payload.repair_description = form.repair_description || null
      payload.parts = form.parts.map(p => ({
        part_name: p.part_name,
        part_spec: p.part_spec || null,
        quantity: p.quantity,
        unit: p.unit || '个',
        unit_price: p.unit_price || 0,
      }))
      await updateRepair(editingId.value, payload)
      ElMessage.success('修改成功')
    } else {
      await createRepair(payload)
      ElMessage.success('维修工单已创建')
    }
    drawerVisible.value = false
    loadList()
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

// --- 删除 ---
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除工单 ${row.repair_no}？`, '确认', { type: 'warning' })
    await deleteRepair(row.id)
    ElMessage.success('已删除')
    loadList()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.message || '删除失败')
  }
}

// --- AI 诊断 ---
async function handleAiDiagnose(row) {
  const equipmentCode = row?.equipment_code
  const faultDesc = row?.fault_description
  if (!equipmentCode || !faultDesc) {
    ElMessage.warning('当前行缺少设备编号或故障描述，无法诊断')
    return
  }
  if (diagnoseLoadingId.value != null) return

  diagnoseLoadingId.value = row.id
  const loadingMsg = ElMessage({
    message: 'AI 诊断中，请稍候…',
    duration: 0,
    type: 'info',
  })

  try {
    const res = await requestAiDiagnose({
      repairId: row.id,
      equipmentCode,
      equipmentName: row.equipment_name || undefined,
      faultDesc,
      user: user.value?.username || undefined,
    })

    if (res?.code === 0 && res?.data?.diagnosis) {
      diagnoseHtml.value = renderMarkdownLite(res.data.diagnosis)
      diagnoseDialogVisible.value = true
    } else {
      ElMessage.error(res?.message || '诊断服务暂不可用')
    }
  } catch (err) {
    console.error('AI诊断失败', err)
    ElMessage.error('诊断服务暂不可用')
  } finally {
    loadingMsg.close()
    diagnoseLoadingId.value = null
  }
}

onMounted(loadList)
</script>

<style scoped>
.repair-management {
  min-height: 100%;
  background: #eef0f3;
}

/* 页首 */
.repair-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 22px;
  background: #2c3540;
  border-left: 4px solid #e6a23c;
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
  background: rgba(230, 162, 60, 0.15);
  border: 1px solid rgba(230, 162, 60, 0.4);
  border-radius: 4px;
  color: #e6a23c;
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
  background: rgba(230, 162, 60, 0.12);
}

.pipe-count {
  font-size: 20px;
  font-weight: 700;
  color: #e6a23c;
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

/* 搜索筛选 */
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

.toolbar-spacer {
  flex: 1;
}

.pcb-fault-strip {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  margin-bottom: 12px;
  background: #fff;
  border: 1px solid #d8dde3;
  border-radius: 4px;
}

.pcb-fault-strip__label {
  flex-shrink: 0;
  padding-top: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #606266;
}

.pcb-fault-scroll {
  flex: 1;
  min-width: 0;
}

.pcb-fault-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-bottom: 2px;
}

.pcb-fault-chip {
  border: 1px solid #dcdfe6;
  background: #f5f7fa;
  color: #606266;
  font-size: 12px;
  line-height: 1.4;
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.pcb-fault-chip:hover,
.pcb-fault-chip.active {
  border-color: #e6a23c;
  background: #fdf6ec;
  color: #b45309;
}

.pcb-fault-clear {
  flex-shrink: 0;
  margin-top: 2px;
}

.pcb-demo-tag {
  margin-left: 6px;
  vertical-align: middle;
}

/* 表格 */
.table-wrap {
  background: #fff;
  border: 1px solid #d8dde3;
  border-radius: 4px;
  padding: 12px;
}

.repair-no {
  font-family: monospace;
  font-size: 13px;
  color: #b06a2e;
  font-weight: 600;
}

.cell-equipment {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.equip-name {
  font-size: 14px;
  font-weight: 500;
}

.equip-code {
  font-size: 11px;
  color: #909399;
}

.urgency-tag {
  display: inline-block;
  padding: 2px 8px;
  font-size: 12px;
  border-radius: 2px;
  font-weight: 500;
}

.urg-low { color: #909399; background: #f4f4f5; border: 1px solid #e9e9eb; }
.urg-normal { color: #409eff; background: #ecf5ff; border: 1px solid #b3d8ff; }
.urg-high { color: #e6a23c; background: #fdf6ec; border: 1px solid #f5dab1; }
.urg-urgent { color: #f56c6c; background: #fef0f0; border: 1px solid #fbc4c4; }

.repair-status {
  display: inline-block;
  padding: 2px 8px;
  font-size: 12px;
  border-radius: 2px;
}

.rs-pending { color: #b45309; background: #fffbeb; border: 1px solid #fcd34d; }
.rs-in_progress { color: #1d4ed8; background: #eff6ff; border: 1px solid #93c5fd; }
.rs-completed { color: #15803d; background: #f0fdf4; border: 1px solid #86efac; }
.rs-closed { color: #64748b; background: #f1f5f9; border: 1px solid #cbd5e1; }

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

/* 抽屉表单 */
.repair-form {
  padding: 0 8px;
}

.parts-editor {
  width: 100%;
}

.part-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.upload-hint {
  font-size: 12px;
  color: #909399;
  margin: 4px 0 0;
}

.ai-diagnose-md {
  max-height: 60vh;
  overflow: auto;
  font-size: 14px;
  line-height: 1.65;
  color: #1f2937;
  word-break: break-word;
}

.ai-diagnose-md :deep(p) {
  margin: 0 0 10px;
}

.ai-diagnose-md :deep(ul),
.ai-diagnose-md :deep(ol) {
  margin: 0 0 12px 1.2em;
  padding: 0;
}

.ai-diagnose-md :deep(li) {
  margin: 4px 0;
}

.ai-diagnose-md :deep(h3),
.ai-diagnose-md :deep(h4),
.ai-diagnose-md :deep(h5) {
  margin: 12px 0 8px;
  font-size: 15px;
  font-weight: 600;
}

.ai-diagnose-md :deep(strong) {
  font-weight: 600;
  color: #111827;
}

.ai-diagnose-md :deep(code) {
  background: #f3f4f6;
  padding: 1px 4px;
  border-radius: 4px;
  font-size: 0.92em;
}

.ai-diagnose-md :deep(table.md-table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 14px;
  font-size: 13px;
}

.ai-diagnose-md :deep(table.md-table th),
.ai-diagnose-md :deep(table.md-table td) {
  border: 1px solid #e5e7eb;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

.ai-diagnose-md :deep(table.md-table th) {
  background: #f9fafb;
  font-weight: 600;
}
</style>
