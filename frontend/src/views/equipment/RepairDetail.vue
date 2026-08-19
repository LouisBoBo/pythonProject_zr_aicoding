<template>
  <div class="repair-detail" v-loading="loading">
    <!-- 面包屑导航 -->
    <div class="breadcrumb-bar">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/equipment/repairs' }">维修管理</el-breadcrumb-item>
        <el-breadcrumb-item>{{ detail.repair_no || '维修详情' }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 工单信息卡片 -->
    <div class="info-card">
      <div class="card-header">
        <div class="header-main">
          <h2 class="repair-no-title">{{ detail.repair_no }}</h2>
          <span class="repair-status-lg" :class="'rs-' + detail.status">{{ statusLabel(detail.status) }}</span>
          <span class="urgency-tag-lg" :class="'urg-' + detail.urgency">{{ urgencyLabel(detail.urgency) }}</span>
        </div>
        <div class="header-actions">
          <el-button v-if="detail.status === 'pending'" type="warning" @click="changeStatus('in_progress')">
            开始维修
          </el-button>
          <el-button v-if="detail.status === 'in_progress'" type="success" @click="changeStatus('completed')">
            维修完成
          </el-button>
          <el-button
            v-if="detail.status === 'pending' || detail.status === 'in_progress'"
            type="info"
            @click="changeStatus('closed')"
          >
            关闭工单
          </el-button>
          <el-button @click="openEditDrawer">编辑</el-button>
        </div>
      </div>

      <div class="card-body">
        <el-descriptions :column="3" border size="default">
          <el-descriptions-item label="设备名称">{{ detail.equipment_name }}</el-descriptions-item>
          <el-descriptions-item label="设备编号">{{ detail.equipment_code }}</el-descriptions-item>
          <el-descriptions-item label="故障分类">{{ detail.fault_category }}</el-descriptions-item>
          <el-descriptions-item label="报修人">{{ detail.reporter }}</el-descriptions-item>
          <el-descriptions-item label="报修时间">{{ formatDateTime(detail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="维修人员">{{ detail.repair_person || '待分配' }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatDateTime(detail.start_time) }}</el-descriptions-item>
          <el-descriptions-item label="维修完成时间">{{ formatDateTime(detail.repair_completed_at, true) }}</el-descriptions-item>
          <el-descriptions-item label="故障描述" :span="3">
            <p class="desc-text">{{ detail.fault_description }}</p>
          </el-descriptions-item>
          <el-descriptions-item v-if="detail.repair_description" label="维修描述" :span="3">
            <p class="desc-text">{{ detail.repair_description }}</p>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </div>

    <!-- 进度时间轴 + 配件清单 并排 -->
    <div class="detail-grid">
      <!-- 进度时间轴 -->
      <div class="timeline-card">
        <h3 class="section-title">
          <el-icon><Clock /></el-icon> 维修进度
        </h3>
        <div class="timeline">
          <div class="tl-item" :class="{ active: true }">
            <div class="tl-dot done" />
            <div class="tl-content">
              <div class="tl-title">工单创建</div>
              <div class="tl-meta">{{ formatDateTime(detail.created_at) }}</div>
              <div class="tl-desc">{{ detail.reporter }} 提交报修</div>
            </div>
          </div>

          <div class="tl-item" :class="{ active: detail.status !== 'pending' }">
            <div class="tl-dot" :class="detail.status !== 'pending' ? 'done' : 'pending'" />
            <div class="tl-content">
              <div class="tl-title">维修派工</div>
              <div class="tl-meta">{{ formatDateTime(detail.start_time) }}</div>
              <div class="tl-desc">{{ detail.repair_person ? `${detail.repair_person} 接单` : '等待分配' }}</div>
            </div>
          </div>

          <div class="tl-item" :class="{ active: detail.status === 'in_progress' || detail.status === 'completed' }">
            <div class="tl-dot" :class="detail.status === 'in_progress' || detail.status === 'completed' ? 'doing' : 'pending'" />
            <div class="tl-content">
              <div class="tl-title">维修进行</div>
              <div class="tl-meta">{{ detail.status === 'in_progress' || detail.status === 'completed' ? '处理中' : '未开始' }}</div>
              <div class="tl-desc">{{ detail.repair_description || '等待维修处理' }}</div>
            </div>
          </div>

          <div class="tl-item" :class="{ active: detail.status === 'completed' || detail.status === 'closed' }">
            <div class="tl-dot" :class="detail.status === 'completed' || detail.status === 'closed' ? 'done' : 'pending'" />
            <div class="tl-content">
              <div class="tl-title">维修完成</div>
              <div class="tl-meta">{{ formatDateTime(detail.repair_completed_at, true) }}</div>
              <div class="tl-desc">{{ detail.status === 'completed' || detail.status === 'closed' ? '工单已完成' : '待完成' }}</div>
            </div>
          </div>

          <div v-if="detail.status === 'closed'" class="tl-item active">
            <div class="tl-dot closed" />
            <div class="tl-content">
              <div class="tl-title">工单关闭</div>
              <div class="tl-desc">工单已归档关闭</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 配件清单 + 费用汇总 -->
      <div class="parts-card">
        <h3 class="section-title">
          <el-icon><List /></el-icon> 更换配件清单
        </h3>
        <el-table :data="detail.parts || []" border size="small" empty-text="暂无配件记录">
          <el-table-column prop="part_name" label="配件名称" min-width="120" />
          <el-table-column prop="part_spec" label="规格" min-width="90">
            <template #default="{ row }">{{ row.part_spec || '-' }}</template>
          </el-table-column>
          <el-table-column prop="quantity" label="数量" width="60" align="center" />
          <el-table-column prop="unit" label="单位" width="50" align="center" />
          <el-table-column label="单价(元)" width="100" align="right">
            <template #default="{ row }">{{ row.unit_price.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="小计(元)" width="100" align="right">
            <template #default="{ row }">{{ (row.quantity * row.unit_price).toFixed(2) }}</template>
          </el-table-column>
        </el-table>

        <!-- 费用汇总 -->
        <div class="cost-summary" v-if="detail.parts && detail.parts.length">
          <div class="cost-row">
            <span>配件合计</span>
            <span class="cost-value">¥ {{ partsTotal.toFixed(2) }}</span>
          </div>
          <div class="cost-row">
            <span>人工费（估算）</span>
            <span class="cost-value">¥ {{ laborCost.toFixed(2) }}</span>
          </div>
          <el-divider style="margin: 8px 0" />
          <div class="cost-row total">
            <span>费用总计</span>
            <span class="cost-value">¥ {{ (partsTotal + laborCost).toFixed(2) }}</span>
          </div>
        </div>
        <div v-else class="no-parts-hint">暂无配件更换记录，费用为 0</div>
      </div>
    </div>

    <!-- 编辑抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      title="编辑维修工单"
      size="520px"
      destroy-on-close
    >
      <el-form ref="editFormRef" :model="editForm" label-width="90px" class="repair-form">
        <el-form-item label="故障分类">
          <el-select v-model="editForm.fault_category" style="width: 100%">
            <el-option v-for="cat in faultCategories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item label="紧急程度">
          <el-radio-group v-model="editForm.urgency">
            <el-radio-button value="low">低</el-radio-button>
            <el-radio-button value="normal">普通</el-radio-button>
            <el-radio-button value="high">紧急</el-radio-button>
            <el-radio-button value="urgent">特急</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" style="width: 100%">
            <el-option label="待处理" value="pending" />
            <el-option label="处理中" value="in_progress" />
            <el-option label="已完成" value="completed" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item label="维修人员">
          <el-input v-model="editForm.repair_person" maxlength="50" />
        </el-form-item>
        <el-form-item label="维修描述">
          <el-input v-model="editForm.repair_description" type="textarea" :rows="3" maxlength="2000" show-word-limit />
        </el-form-item>
        <el-divider content-position="left">更换配件</el-divider>
        <div class="parts-editor">
          <div v-for="(part, idx) in editForm.parts" :key="idx" class="part-row">
            <el-input v-model="part.part_name" placeholder="名称" size="small" style="width: 110px" />
            <el-input v-model="part.part_spec" placeholder="规格" size="small" style="width: 80px" />
            <el-input-number v-model="part.quantity" :min="1" size="small" style="width: 60px" />
            <el-input v-model="part.unit" placeholder="单位" size="small" style="width: 50px" />
            <el-input-number v-model="part.unit_price" :min="0" :precision="2" size="small" style="width: 90px" controls-position="right" />
            <el-button link type="danger" size="small" @click="removeEditPart(idx)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <el-button link type="primary" size="small" :icon="Plus" @click="addEditPart">添加配件</el-button>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="drawerVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleEditSubmit">保存修改</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Clock, List, Plus, Delete } from '@element-plus/icons-vue'
import { fetchRepairDetail, updateRepair } from '../../api/equipmentRepair'

const route = useRoute()
const router = useRouter()

const repairId = computed(() => Number(route.params.id))

const loading = ref(false)
const submitting = ref(false)
const detail = ref({
  repair_no: '',
  equipment_code: '',
  equipment_name: '',
  fault_category: '',
  fault_description: '',
  urgency: 'normal',
  status: 'pending',
  reporter: '',
  repair_person: null,
  start_time: null,
  repair_completed_at: null,
  repair_description: null,
  parts: [],
  created_at: null,
})

const faultCategories = [
  '机械故障', '电气故障', '液压故障', '气动故障',
  '控制系统故障', '传动故障', '润滑故障', '其他',
]

const drawerVisible = ref(false)
const editFormRef = ref(null)
const editForm = reactive({
  fault_category: '',
  urgency: 'normal',
  status: 'pending',
  repair_person: '',
  repair_description: '',
  parts: [],
})

// 费用计算
const partsTotal = computed(() =>
  (detail.value.parts || []).reduce((s, p) => s + (p.quantity || 0) * (p.unit_price || 0), 0),
)

const laborCost = computed(() => {
  const count = (detail.value.parts || []).length
  if (!count) return 0
  return count * 150 // 估算每个配件更换人工 150 元
})

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

async function loadDetail() {
  loading.value = true
  try {
    const res = await fetchRepairDetail(repairId.value)
    detail.value = res
  } catch (err) {
    ElMessage.error(err.message || '加载详情失败')
    router.replace('/equipment/repairs')
  } finally {
    loading.value = false
  }
}

async function changeStatus(newStatus) {
  submitting.value = true
  try {
    const payload = { status: newStatus }
    await updateRepair(repairId.value, payload)
    ElMessage.success(`状态已更新为「${statusLabel(newStatus)}」`)
    loadDetail()
  } catch (err) {
    ElMessage.error(err.message || '状态更新失败')
  } finally {
    submitting.value = false
  }
}

// 编辑
function openEditDrawer() {
  Object.assign(editForm, {
    fault_category: detail.value.fault_category,
    urgency: detail.value.urgency,
    status: detail.value.status,
    repair_person: detail.value.repair_person || '',
    repair_description: detail.value.repair_description || '',
    parts: (detail.value.parts || []).map(p => ({ ...p })),
  })
  drawerVisible.value = true
}

function addEditPart() {
  editForm.parts.push({ part_name: '', part_spec: '', quantity: 1, unit: '个', unit_price: 0 })
}

function removeEditPart(idx) {
  editForm.parts.splice(idx, 1)
}

async function handleEditSubmit() {
  submitting.value = true
  try {
    await updateRepair(repairId.value, {
      fault_category: editForm.fault_category,
      urgency: editForm.urgency,
      status: editForm.status,
      repair_person: editForm.repair_person || null,
      repair_description: editForm.repair_description || null,
      parts: editForm.parts.map(p => ({
        part_name: p.part_name,
        part_spec: p.part_spec || null,
        quantity: p.quantity,
        unit: p.unit || '个',
        unit_price: p.unit_price || 0,
      })),
    })
    ElMessage.success('修改成功')
    drawerVisible.value = false
    loadDetail()
  } catch (err) {
    ElMessage.error(err.message || '修改失败')
  } finally {
    submitting.value = false
  }
}

onMounted(loadDetail)
</script>

<style scoped>
.repair-detail {
  min-height: 100%;
  padding-bottom: 32px;
}

.breadcrumb-bar {
  margin-bottom: 16px;
}

/* 信息卡片 */
.info-card {
  background: #fff;
  border: 1px solid #dce3eb;
  border-radius: 4px;
  margin-bottom: 16px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: #f8fafc;
  border-bottom: 1px solid #eef1f5;
}

.header-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.repair-no-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  font-family: monospace;
  color: #303133;
}

.repair-status-lg {
  display: inline-block;
  padding: 3px 12px;
  font-size: 13px;
  border-radius: 4px;
  font-weight: 600;
}

.urgency-tag-lg {
  display: inline-block;
  padding: 3px 12px;
  font-size: 13px;
  border-radius: 4px;
  font-weight: 600;
}

.card-body {
  padding: 20px;
}

.desc-text {
  margin: 0;
  line-height: 1.6;
  color: #4a5568;
}

/* 双栏 */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.timeline-card,
.parts-card {
  background: #fff;
  border: 1px solid #dce3eb;
  border-radius: 4px;
  padding: 16px 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

/* 时间轴 */
.timeline {
  padding-left: 8px;
}

.tl-item {
  display: flex;
  gap: 12px;
  padding-bottom: 20px;
  position: relative;
  opacity: 0.45;
}

.tl-item.active {
  opacity: 1;
}

.tl-item:not(:last-child)::after {
  content: '';
  position: absolute;
  left: 6px;
  top: 14px;
  width: 2px;
  height: calc(100% - 4px);
  background: #dce3eb;
}

.tl-item.active:not(:last-child)::after {
  background: #409eff;
}

.tl-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 2px;
  background: #dce3eb;
}

.tl-dot.done { background: #67c23a; }
.tl-dot.doing { background: #409eff; animation: pulse 1.5s infinite; }
.tl-dot.pending { background: #e6a23c; }
.tl-dot.closed { background: #909399; }

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(64, 158, 255, 0.4); }
  50% { box-shadow: 0 0 0 6px rgba(64, 158, 255, 0); }
}

.tl-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.tl-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.tl-desc {
  font-size: 13px;
  color: #606266;
  margin-top: 4px;
}

/* 配件 */
.cost-summary {
  margin-top: 16px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 4px;
}

.cost-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 14px;
  color: #606266;
}

.cost-row.total {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
}

.cost-value {
  font-family: monospace;
  font-weight: 600;
}

.no-parts-hint {
  text-align: center;
  color: #909399;
  padding: 24px 0;
  font-size: 13px;
}

/* 状态颜色复用 */
.rs-pending { color: #b45309; background: #fffbeb; border: 1px solid #fcd34d; }
.rs-in_progress { color: #1d4ed8; background: #eff6ff; border: 1px solid #93c5fd; }
.rs-completed { color: #15803d; background: #f0fdf4; border: 1px solid #86efac; }
.rs-closed { color: #64748b; background: #f1f5f9; border: 1px solid #cbd5e1; }

.urg-low { color: #909399; background: #f4f4f5; border: 1px solid #e9e9eb; }
.urg-normal { color: #409eff; background: #ecf5ff; border: 1px solid #b3d8ff; }
.urg-high { color: #e6a23c; background: #fdf6ec; border: 1px solid #f5dab1; }
.urg-urgent { color: #f56c6c; background: #fef0f0; border: 1px solid #fbc4c4; }

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
</style>
