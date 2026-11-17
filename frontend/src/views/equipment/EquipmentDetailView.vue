<template>
  <div v-loading="loading" class="equipment-detail">
    <el-breadcrumb separator="/" class="breadcrumb">
      <el-breadcrumb-item :to="{ path: '/equipment/ledger' }">设备管理</el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: '/equipment/ledger' }">设备台账</el-breadcrumb-item>
      <el-breadcrumb-item>{{ equipment?.name || '设备详情' }}</el-breadcrumb-item>
    </el-breadcrumb>

    <template v-if="equipment">
      <!-- 基本信息：主视觉层级 -->
      <div class="info-primary">
        <div class="primary-header">
          <div class="code-block">
            <span class="code-label">设备编号</span>
            <span class="code-value">{{ equipment.equipment_code }}</span>
          </div>
          <span class="eq-status" :class="'eq-status-' + equipment.status">
            {{ equipment.status }}
          </span>
          <span
            v-if="maintStatus"
            class="maint-status-tag"
            :class="'maint-' + maintStatus.alert_level"
          >
            {{ maintStatus.status_label }}
          </span>
        </div>
        <h2 class="eq-name">{{ equipment.name }}</h2>
        <div class="primary-grid">
          <div class="grid-cell">
            <span class="cell-label">规格型号</span>
            <span class="cell-value">{{ equipment.spec_model || '-' }}</span>
          </div>
          <div class="grid-cell">
            <span class="cell-label">使用部门</span>
            <span class="cell-value">{{ equipment.department || '-' }}</span>
          </div>
          <div class="grid-cell">
            <span class="cell-label">安装位置</span>
            <span class="cell-value">{{ equipment.location || '-' }}</span>
          </div>
        </div>
      </div>

      <!-- 保养状态 -->
      <div v-if="maintStatus" class="info-maintenance">
        <h3 class="section-title">保养状态</h3>
        <div class="maint-summary">
          <div class="maint-cell">
            <span class="maint-label">状态</span>
            <span
              class="maint-value maint-value-tag"
              :class="'maint-' + maintStatus.alert_level"
            >
              {{ maintStatus.status_label }}
            </span>
          </div>
          <div v-if="maintStatus.active_plans > 0" class="maint-cell">
            <span class="maint-label">启用计划</span>
            <span class="maint-value">{{ maintStatus.active_plans }}</span>
          </div>
          <div v-if="maintStatus.pending_orders > 0" class="maint-cell">
            <span class="maint-label">待办工单</span>
            <span class="maint-value">{{ maintStatus.pending_orders }}</span>
          </div>
          <div v-if="maintStatus.next_due_at" class="maint-cell">
            <span class="maint-label">下次到期</span>
            <span class="maint-value">{{ formatMaintDue(maintStatus.next_due_at) }}</span>
          </div>
          <router-link
            v-if="maintStatus.active_plans > 0 || maintStatus.pending_orders > 0"
            :to="{ path: '/equipment/maintenance-orders', query: { equipment_id: equipment.id } }"
            class="maint-link"
          >
            查看保养工单 →
          </router-link>
        </div>
      </div>

      <!-- 扩展信息：次级视觉层级 -->
      <div class="info-secondary">
        <h3 class="section-title">扩展信息</h3>
        <div class="secondary-grid">
          <div class="sec-cell">
            <span class="sec-label">购置日期</span>
            <span class="sec-value">{{ equipment.purchase_date || '-' }}</span>
          </div>
          <div class="sec-cell">
            <span class="sec-label">启用日期</span>
            <span class="sec-value">{{ equipment.commission_date || '-' }}</span>
          </div>
          <div class="sec-cell">
            <span class="sec-label">供应商/制造商</span>
            <span class="sec-value">{{ equipment.supplier || '-' }}</span>
          </div>
          <div class="sec-cell full">
            <span class="sec-label">备注</span>
            <span class="sec-value">{{ equipment.remark || '-' }}</span>
          </div>
          <div class="sec-cell">
            <span class="sec-label">创建时间</span>
            <span class="sec-value">{{ formatDateTime(equipment.created_at) }}</span>
          </div>
          <div class="sec-cell">
            <span class="sec-label">更新时间</span>
            <span class="sec-value">{{ formatDateTime(equipment.updated_at) }}</span>
          </div>
        </div>
      </div>

      <div class="detail-actions">
        <el-button @click="goBack">返回列表</el-button>
        <el-button type="primary" @click="openEditDialog">编辑设备</el-button>
      </div>
    </template>

    <!-- 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      title="编辑设备"
      width="580px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px">
        <el-form-item label="设备编号" prop="equipment_code">
          <el-input v-model="form.equipment_code" maxlength="50" />
        </el-form-item>
        <el-form-item label="设备名称" prop="name">
          <el-input v-model="form.name" maxlength="100" />
        </el-form-item>
        <el-form-item label="规格型号">
          <el-input v-model="form.spec_model" maxlength="100" />
        </el-form-item>
        <el-form-item label="使用部门">
          <el-input v-model="form.department" maxlength="50" />
        </el-form-item>
        <el-form-item label="安装位置">
          <el-input v-model="form.location" maxlength="100" />
        </el-form-item>
        <el-form-item label="设备状态" prop="status">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="运行" value="运行" />
            <el-option label="停机" value="停机" />
            <el-option label="维修" value="维修" />
            <el-option label="报废" value="报废" />
          </el-select>
        </el-form-item>
        <el-form-item label="购置日期">
          <el-date-picker
            v-model="form.purchase_date"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="启用日期">
          <el-date-picker
            v-model="form.commission_date"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="form.supplier" maxlength="100" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchEquipment, updateEquipment } from '../../api/equipment'
import { fetchEquipmentMaintenanceStatus } from '../../api/equipmentMaintenance'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const submitting = ref(false)
const equipment = ref(null)
const maintStatus = ref(null)
const dialogVisible = ref(false)
const formRef = ref(null)

const form = reactive({
  equipment_code: '',
  name: '',
  spec_model: '',
  department: '',
  location: '',
  status: '运行',
  purchase_date: null,
  commission_date: null,
  supplier: '',
  remark: '',
})

const formRules = {
  equipment_code: [{ required: true, message: '请输入设备编号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  status: [{ required: true, message: '请选择设备状态', trigger: 'change' }],
}

function formatDateTime(val) {
  if (!val) return '-'
  const d = new Date(val)
  if (Number.isNaN(d.getTime())) return val
  return d.toLocaleString('zh-CN', { hour12: false })
}

function formatMaintDue(val) {
  if (!val) return '-'
  const d = new Date(val)
  if (Number.isNaN(d.getTime())) return val
  return d.toLocaleDateString('zh-CN')
}

async function loadDetail() {
  loading.value = true
  try {
    equipment.value = await fetchEquipment(route.params.id)
    try {
      maintStatus.value = await fetchEquipmentMaintenanceStatus(route.params.id)
    } catch {
      maintStatus.value = null
    }
  } catch (err) {
    ElMessage.error(err.message || '加载失败')
    router.push('/equipment/ledger')
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/equipment/ledger')
}

function openEditDialog() {
  if (!equipment.value) return
  Object.assign(form, {
    equipment_code: equipment.value.equipment_code,
    name: equipment.value.name,
    spec_model: equipment.value.spec_model || '',
    department: equipment.value.department || '',
    location: equipment.value.location || '',
    status: equipment.value.status,
    purchase_date: equipment.value.purchase_date || null,
    commission_date: equipment.value.commission_date || null,
    supplier: equipment.value.supplier || '',
    remark: equipment.value.remark || '',
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    equipment.value = await updateEquipment(route.params.id, {
      equipment_code: form.equipment_code,
      name: form.name,
      spec_model: form.spec_model || null,
      department: form.department || null,
      location: form.location || null,
      status: form.status,
      purchase_date: form.purchase_date || null,
      commission_date: form.commission_date || null,
      supplier: form.supplier || null,
      remark: form.remark || null,
    })
    dialogVisible.value = false
    ElMessage.success('保存成功')
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    submitting.value = false
  }
}

onMounted(loadDetail)
</script>

<style scoped>
.equipment-detail {
  min-height: 100%;
  background: #eef1f5;
}

.breadcrumb {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #dce3eb;
  border-radius: 4px;
}

/* 基本信息区：蓝灰主卡片 */
.info-primary {
  padding: 24px 28px;
  background: linear-gradient(135deg, #3d4f63 0%, #52667a 100%);
  border-radius: 4px;
  margin-bottom: 12px;
}

.primary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.code-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.code-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.code-value {
  font-size: 14px;
  font-family: 'SF Mono', 'Consolas', monospace;
  color: #b8c9dc;
  letter-spacing: 0.5px;
}

.eq-name {
  margin: 0 0 20px;
  font-size: 22px;
  font-weight: 600;
  color: #f0f4f8;
}

.primary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.grid-cell {
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.12);
  border-radius: 4px;
}

.cell-label {
  display: block;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 4px;
}

.cell-value {
  font-size: 15px;
  color: #fff;
  font-weight: 500;
}

.eq-status {
  display: inline-block;
  padding: 4px 12px;
  font-size: 13px;
  border-radius: 2px;
  font-weight: 500;
}

.eq-status-运行 {
  color: #389e0d;
  background: #f6ffed;
  border: 1px solid #b7eb8f;
}

.eq-status-停机 {
  color: #d48806;
  background: #fffbe6;
  border: 1px solid #ffe58f;
}

.eq-status-维修 {
  color: #d46b08;
  background: #fff7e6;
  border: 1px solid #ffd591;
}

.eq-status-报废 {
  color: #595959;
  background: #f5f5f5;
  border: 1px solid #d9d9d9;
}

/* 扩展信息：次级白底区 */
.info-secondary {
  padding: 20px 24px;
  background: #fff;
  border: 1px solid #dce3eb;
  border-radius: 4px;
  margin-bottom: 12px;
}

.section-title {
  margin: 0 0 16px;
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.secondary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.sec-cell {
  padding: 10px 14px;
  background: #f8fafc;
  border: 1px solid #eef1f5;
  border-radius: 4px;
}

.sec-cell.full {
  grid-column: 1 / -1;
}

.sec-label {
  display: block;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 4px;
}

.sec-value {
  font-size: 14px;
  color: #334155;
}

.detail-actions {
  display: flex;
  gap: 12px;
  padding: 16px 0;
}

.maint-status-tag {
  display: inline-block;
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 2px;
  margin-left: 8px;
}

.maint-none {
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
}

.maint-normal {
  color: #15803d;
  background: #f0fdf4;
  border: 1px solid #86efac;
}

.maint-due_soon {
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fcd34d;
}

.maint-overdue {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fca5a5;
}

.info-maintenance {
  padding: 20px 24px;
  background: #fff;
  border: 1px solid #dce3eb;
  border-left: 3px solid #d4a55a;
  border-radius: 4px;
  margin-bottom: 12px;
}

.maint-summary {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.maint-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.maint-label {
  font-size: 12px;
  color: #94a3b8;
}

.maint-value {
  font-size: 16px;
  font-weight: 600;
  color: #334155;
}

.maint-value-tag {
  font-size: 13px;
  padding: 2px 8px;
  border-radius: 2px;
  font-weight: 500;
}

.maint-link {
  margin-left: auto;
  font-size: 13px;
  color: #8b7355;
  text-decoration: none;
}

.maint-link:hover {
  color: #d4a55a;
}
</style>
