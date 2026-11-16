<template>
  <div class="maint-records">
    <header class="records-hero">
      <div class="hero-main">
        <div class="hero-icon">
          <el-icon><Document /></el-icon>
        </div>
        <div>
          <h1 class="hero-title">设备保养</h1>
          <p class="hero-desc">保养记录登记 · 查询追溯 · 结果归档</p>
        </div>
      </div>
    </header>

    <div class="toolbar">
      <el-input
        v-model="filters.keyword"
        placeholder="记录编号 / 设备 / 保养人"
        clearable
        style="width: 240px"
        :prefix-icon="Search"
        @keyup.enter="handleSearch"
      />
      <el-select
        v-model="filters.equipmentId"
        placeholder="按设备筛选"
        clearable
        filterable
        style="width: 200px"
      >
        <el-option
          v-for="eq in equipmentList"
          :key="eq.id"
          :label="`${eq.equipment_code} · ${eq.name}`"
          :value="eq.id"
        />
      </el-select>
      <el-select v-model="filters.maintenanceType" placeholder="保养类型" clearable style="width: 120px">
        <el-option label="日常" value="routine" />
        <el-option label="定期" value="periodic" />
        <el-option label="故障后" value="post_fault" />
      </el-select>
      <el-select v-model="filters.maintenanceResult" placeholder="状态" clearable style="width: 110px">
        <el-option label="待处理" value="pending" />
        <el-option label="已完成" value="qualified" />
        <el-option label="异常" value="unqualified" />
      </el-select>
      <el-date-picker
        v-model="filters.dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="保养日起"
        end-placeholder="保养日止"
        value-format="YYYY-MM-DD"
        style="width: 260px"
      />
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
      <div class="toolbar-spacer" />
      <el-button type="primary" :icon="Plus" @click="openCreate">新增保养记录</el-button>
    </div>

    <div class="table-wrap">
      <el-table v-loading="loading" :data="items" border>
        <el-table-column prop="record_no" label="记录编号" min-width="140" fixed="left" />
        <el-table-column prop="equipment_code" label="设备编号" width="120" show-overflow-tooltip />
        <el-table-column prop="equipment_name" label="设备名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="保养类型" width="100" align="center">
          <template #default="{ row }">{{ typeLabel(row.maintenance_type) }}</template>
        </el-table-column>
        <el-table-column label="保养日期" width="120">
          <template #default="{ row }">{{ formatDate(row.actual_date || row.planned_date) }}</template>
        </el-table-column>
        <el-table-column prop="maintainer" label="保养人" width="100" />
        <el-table-column
          prop="maintenance_content"
          label="保养内容"
          min-width="200"
          show-overflow-tooltip
        />
        <el-table-column label="下次保养日期" width="120">
          <template #default="{ row }">{{ formatDate(row.next_maintenance_date) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span class="result-tag" :class="'res-' + row.maintenance_result">
              {{ resultLabel(row.maintenance_result) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
        <el-table-column label="操作" width="120" fixed="right">
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
          @change="loadList"
        />
      </div>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑保养记录' : '新增保养记录'"
      width="640px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="设备" prop="equipment_id">
          <el-select
            v-model="form.equipment_id"
            placeholder="选择设备"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="eq in equipmentList"
              :key="eq.id"
              :label="`${eq.equipment_code} · ${eq.name}`"
              :value="eq.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="保养类型" prop="maintenance_type">
          <el-select v-model="form.maintenance_type" style="width: 100%">
            <el-option label="日常" value="routine" />
            <el-option label="定期" value="periodic" />
            <el-option label="故障后" value="post_fault" />
          </el-select>
        </el-form-item>
        <el-form-item label="保养日期" prop="maintenance_date">
          <el-date-picker
            v-model="form.maintenance_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="保养执行日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="下次保养日期" prop="next_maintenance_date">
          <el-date-picker
            v-model="form.next_maintenance_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选填"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="保养人" prop="maintainer">
          <el-input v-model="form.maintainer" maxlength="50" placeholder="执行保养人员" />
        </el-form-item>
        <el-form-item label="保养内容" prop="maintenance_content">
          <el-input
            v-model="form.maintenance_content"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            placeholder="保养项目与执行内容"
          />
        </el-form-item>
        <el-form-item label="状态" prop="maintenance_result">
          <el-radio-group v-model="form.maintenance_result">
            <el-radio-button value="pending">待处理</el-radio-button>
            <el-radio-button value="qualified">已完成</el-radio-button>
            <el-radio-button value="unqualified">异常</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="500" show-word-limit />
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Search, Plus } from '@element-plus/icons-vue'
import {
  fetchMaintenanceRecords,
  createMaintenanceRecord,
  updateMaintenanceRecord,
  deleteMaintenanceRecord,
} from '../../api/equipmentMaintenanceRecords'
import { fetchEquipmentList } from '../../api/equipment'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

const filters = reactive({
  keyword: '',
  equipmentId: null,
  maintenanceType: '',
  maintenanceResult: '',
  dateRange: null,
})

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formRef = ref(null)
const equipmentList = ref([])

const defaultForm = () => ({
  equipment_id: null,
  maintenance_type: 'routine',
  maintenance_date: '',
  next_maintenance_date: '',
  maintainer: '',
  maintenance_content: '',
  maintenance_result: 'qualified',
  remark: '',
})

const form = reactive(defaultForm())

const formRules = {
  equipment_id: [{ required: true, message: '请选择设备', trigger: 'change' }],
  maintenance_type: [{ required: true, message: '请选择保养类型', trigger: 'change' }],
  maintenance_date: [{ required: true, message: '请选择保养日期', trigger: 'change' }],
  maintainer: [{ required: true, message: '请输入保养人', trigger: 'blur' }],
  maintenance_content: [{ required: true, message: '请输入保养内容', trigger: 'blur' }],
  maintenance_result: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

function typeLabel(v) {
  const m = { routine: '日常', periodic: '定期', post_fault: '故障后', overhaul: '故障后' }
  return m[v] || v
}

function resultLabel(v) {
  const m = { qualified: '已完成', unqualified: '异常', pending: '待处理' }
  return m[v] || v
}

function formatDate(val) {
  if (!val) return '—'
  const s = String(val)
  return s.length >= 10 ? s.slice(0, 10) : s
}

function buildQueryParams() {
  const [dateFrom, dateTo] = filters.dateRange || []
  return {
    page: page.value,
    pageSize: pageSize.value,
    keyword: filters.keyword || undefined,
    equipmentId: filters.equipmentId || undefined,
    maintenanceType: filters.maintenanceType || undefined,
    maintenanceResult: filters.maintenanceResult || undefined,
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
  }
}

async function loadList() {
  loading.value = true
  try {
    const res = await fetchMaintenanceRecords(buildQueryParams())
    items.value = res.items
    total.value = res.total
  } catch (err) {
    ElMessage.error(err.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function loadEquipmentList() {
  try {
    const res = await fetchEquipmentList({ page: 1, pageSize: 200 })
    equipmentList.value = res.items
  } catch {
    /* ignore */
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.keyword = ''
  filters.equipmentId = null
  filters.maintenanceType = ''
  filters.maintenanceResult = ''
  filters.dateRange = null
  handleSearch()
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
    equipment_id: row.equipment_id,
    maintenance_type: row.maintenance_type === 'overhaul' ? 'post_fault' : row.maintenance_type,
    maintenance_date: formatDate(row.actual_date || row.planned_date),
    next_maintenance_date: row.next_maintenance_date ? formatDate(row.next_maintenance_date) : '',
    maintainer: row.maintainer,
    maintenance_content: row.maintenance_content,
    maintenance_result: row.maintenance_result,
    remark: row.remark || '',
  })
  dialogVisible.value = true
}

function resetForm() {
  Object.assign(form, defaultForm())
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  const payload = {
    equipment_id: form.equipment_id,
    maintenance_type: form.maintenance_type,
    planned_date: form.maintenance_date,
    actual_date: form.maintenance_date,
    next_maintenance_date: form.next_maintenance_date || null,
    maintainer: form.maintainer,
    maintenance_content: form.maintenance_content,
    maintenance_result: form.maintenance_result,
    remark: form.remark || null,
  }
  try {
    if (isEdit.value) {
      await updateMaintenanceRecord(editingId.value, payload)
      ElMessage.success('已保存')
    } else {
      await createMaintenanceRecord(payload)
      ElMessage.success('保养记录已创建')
    }
    dialogVisible.value = false
    loadList()
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除记录「${row.record_no}」？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteMaintenanceRecord(row.id)
    ElMessage.success('已删除')
    loadList()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.message || '删除失败')
  }
}

onMounted(() => {
  loadEquipmentList()
  loadList()
})
</script>

<style scoped>
.maint-records {
  min-height: 100%;
  background: #f4f2ed;
}

.records-hero {
  display: flex;
  align-items: center;
  padding: 20px 24px;
  background: linear-gradient(120deg, #3d5248 0%, #4a5f54 55%, #5c5044 100%);
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

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 4px;
  margin-bottom: 12px;
}

.toolbar-spacer {
  flex: 1;
  min-width: 8px;
}

.table-wrap {
  background: #fff;
  border-radius: 4px;
  padding: 12px 16px 16px;
}

.result-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.res-qualified {
  background: #e8f5e9;
  color: #2e7d32;
}

.res-unqualified {
  background: #ffebee;
  color: #c62828;
}

.res-pending {
  background: #fff8e1;
  color: #f57f17;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
