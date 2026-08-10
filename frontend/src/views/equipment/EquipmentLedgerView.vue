<template>
  <div class="equipment-ledger">
    <!-- 状态概览条：数据密集型页首，非仪表盘卡片 -->
    <div class="ledger-header">
      <div class="header-left">
        <div class="header-icon">
          <el-icon><Cpu /></el-icon>
        </div>
        <div>
          <h1 class="header-title">设备台账</h1>
          <p class="header-desc">资产编号 · 状态 · 部门 · 位置全量检索</p>
        </div>
      </div>
      <div class="status-strip">
        <div class="status-item">
          <span class="status-num">{{ statusCounts.total }}</span>
          <span class="status-label">全部设备</span>
        </div>
        <div class="status-divider" />
        <div v-for="s in statusSummary" :key="s.value" class="status-item">
          <span class="status-dot" :class="'dot-' + s.value" />
          <span class="status-num">{{ s.count }}</span>
          <span class="status-label">{{ s.label }}</span>
        </div>
      </div>
    </div>

    <!-- 筛选区 -->
    <div class="filter-panel">
      <el-form :model="filters" inline class="filter-form">
        <el-form-item label="设备编号">
          <el-input
            v-model="filters.equipmentCode"
            placeholder="编号"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="设备名称">
          <el-input
            v-model="filters.name"
            placeholder="名称"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="使用部门">
          <el-input
            v-model="filters.department"
            placeholder="部门"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="设备状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 110px">
            <el-option label="运行" value="运行" />
            <el-option label="停机" value="停机" />
            <el-option label="维修" value="维修" />
            <el-option label="报废" value="报废" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      <div class="action-group">
        <el-button type="primary" :icon="Plus" @click="openCreateDialog">新增设备</el-button>
        <el-upload
          :show-file-list="false"
          accept=".xlsx,.xls"
          :before-upload="handleImport"
        >
          <el-button :icon="Upload">导入 Excel</el-button>
        </el-upload>
        <el-button :icon="Download" :loading="exporting" @click="handleExport">导出 Excel</el-button>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-panel">
      <el-table v-loading="loading" :data="items" border stripe class="ledger-table">
        <el-table-column prop="equipment_code" label="设备编号" min-width="130" fixed="left" />
        <el-table-column prop="name" label="设备名称" min-width="140" />
        <el-table-column prop="spec_model" label="规格型号" min-width="120">
          <template #default="{ row }">{{ row.spec_model || '-' }}</template>
        </el-table-column>
        <el-table-column prop="department" label="使用部门" min-width="110">
          <template #default="{ row }">{{ row.department || '-' }}</template>
        </el-table-column>
        <el-table-column prop="location" label="安装位置" min-width="100">
          <template #default="{ row }">{{ row.location || '-' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="设备状态" width="90" align="center">
          <template #default="{ row }">
            <span class="eq-status" :class="'eq-status-' + row.status">{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="purchase_date" label="购置日期" width="110">
          <template #default="{ row }">{{ row.purchase_date || '-' }}</template>
        </el-table-column>
        <el-table-column prop="commission_date" label="启用日期" width="110">
          <template #default="{ row }">{{ row.commission_date || '-' }}</template>
        </el-table-column>
        <el-table-column prop="supplier" label="供应商" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.supplier || '-' }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="goDetail(row)">详情</el-button>
            <el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
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
          @size-change="loadList"
          @current-change="loadList"
        />
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑设备' : '新增设备'"
      width="580px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px">
        <el-form-item label="设备编号" prop="equipment_code">
          <el-input v-model="form.equipment_code" placeholder="唯一编号" maxlength="50" />
        </el-form-item>
        <el-form-item label="设备名称" prop="name">
          <el-input v-model="form.name" placeholder="设备名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="规格型号" prop="spec_model">
          <el-input v-model="form.spec_model" placeholder="规格型号" maxlength="100" />
        </el-form-item>
        <el-form-item label="使用部门" prop="department">
          <el-input v-model="form.department" placeholder="使用部门" maxlength="50" />
        </el-form-item>
        <el-form-item label="安装位置" prop="location">
          <el-input v-model="form.location" placeholder="安装位置" maxlength="100" />
        </el-form-item>
        <el-form-item label="设备状态" prop="status">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="运行" value="运行" />
            <el-option label="停机" value="停机" />
            <el-option label="维修" value="维修" />
            <el-option label="报废" value="报废" />
          </el-select>
        </el-form-item>
        <el-form-item label="购置日期" prop="purchase_date">
          <el-date-picker
            v-model="form.purchase_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="启用日期" prop="commission_date">
          <el-date-picker
            v-model="form.commission_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="供应商" prop="supplier">
          <el-input v-model="form.supplier" placeholder="供应商/制造商" maxlength="100" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Cpu, Plus, Upload, Download } from '@element-plus/icons-vue'
import {
  fetchEquipmentList,
  createEquipment,
  updateEquipment,
  deleteEquipment,
  importEquipment,
  exportEquipment,
} from '../../api/equipment'

const router = useRouter()

const loading = ref(false)
const exporting = ref(false)
const submitting = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const allItems = ref([])

const filters = reactive({
  equipmentCode: '',
  name: '',
  department: '',
  status: '',
})

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const defaultForm = () => ({
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

const form = reactive(defaultForm())

const formRules = {
  equipment_code: [{ required: true, message: '请输入设备编号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  status: [{ required: true, message: '请选择设备状态', trigger: 'change' }],
}

const STATUS_LIST = [
  { value: '运行', label: '运行' },
  { value: '停机', label: '停机' },
  { value: '维修', label: '维修' },
  { value: '报废', label: '报废' },
]

const statusCounts = computed(() => {
  const counts = { total: allItems.value.length }
  for (const s of STATUS_LIST) {
    counts[s.value] = allItems.value.filter((i) => i.status === s.value).length
  }
  return counts
})

const statusSummary = computed(() =>
  STATUS_LIST.map((s) => ({
    ...s,
    count: statusCounts.value[s.value] || 0,
  })),
)

function buildQueryParams() {
  return {
    page: page.value,
    pageSize: pageSize.value,
    equipmentCode: filters.equipmentCode || undefined,
    name: filters.name || undefined,
    department: filters.department || undefined,
    status: filters.status || undefined,
  }
}

async function loadAllForStats() {
  try {
    const res = await fetchEquipmentList({ page: 1, pageSize: 100 })
    allItems.value = res.items
  } catch {
    allItems.value = []
  }
}

async function loadList() {
  loading.value = true
  try {
    const res = await fetchEquipmentList(buildQueryParams())
    items.value = res.items
    total.value = res.total
  } catch (err) {
    ElMessage.error(err.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.equipmentCode = ''
  filters.name = ''
  filters.department = ''
  filters.status = ''
  page.value = 1
  loadList()
}

function goDetail(row) {
  router.push(`/equipment/ledger/${row.id}`)
}

function openCreateDialog() {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  editingId.value = row.id
  Object.assign(form, {
    equipment_code: row.equipment_code,
    name: row.name,
    spec_model: row.spec_model || '',
    department: row.department || '',
    location: row.location || '',
    status: row.status,
    purchase_date: row.purchase_date || null,
    commission_date: row.commission_date || null,
    supplier: row.supplier || '',
    remark: row.remark || '',
  })
  dialogVisible.value = true
}

function resetForm() {
  Object.assign(form, defaultForm())
  formRef.value?.resetFields()
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = {
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
    }
    if (isEdit.value) {
      await updateEquipment(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await createEquipment(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadAllForStats()
    loadList()
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除设备「${row.name}」？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteEquipment(row.id)
    ElMessage.success('已删除')
    await loadAllForStats()
    loadList()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.message || '删除失败')
    }
  }
}

async function handleImport(file) {
  try {
    const result = await importEquipment(file)
    ElMessage.success(`导入完成：新增 ${result.created} 条，跳过 ${result.skipped} 条`)
    if (result.errors?.length) {
      ElMessage.warning(result.errors.slice(0, 3).join('；'))
    }
    await loadAllForStats()
    loadList()
  } catch (err) {
    ElMessage.error(err.message || '导入失败')
  }
  return false
}

async function handleExport() {
  exporting.value = true
  try {
    const blob = await exportEquipment({
      equipmentCode: filters.equipmentCode || undefined,
      name: filters.name || undefined,
      department: filters.department || undefined,
      status: filters.status || undefined,
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `设备台账_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (err) {
    ElMessage.error(err.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  loadAllForStats()
  loadList()
})
</script>

<style scoped>
.equipment-ledger {
  min-height: 100%;
  background: #eef1f5;
}

/* 页首：蓝灰基调横条，区别于首页四宫格仪表盘 */
.ledger-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 24px;
  background: linear-gradient(135deg, #3d4f63 0%, #52667a 100%);
  border-radius: 4px;
  margin-bottom: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-icon {
  width: 44px;
  height: 44px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #b8c9dc;
  font-size: 22px;
}

.header-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #f0f4f8;
}

.header-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.55);
}

.status-strip {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 10px 20px;
  background: rgba(0, 0, 0, 0.15);
  border-radius: 4px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-num {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  font-variant-numeric: tabular-nums;
}

.status-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.status-divider {
  width: 1px;
  height: 28px;
  background: rgba(255, 255, 255, 0.15);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-运行 { background: #52c41a; }
.dot-停机 { background: #faad14; }
.dot-维修 { background: #fa8c16; }
.dot-报废 { background: #8c8c8c; }

/* 筛选面板 */
.filter-panel {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 16px 20px;
  background: #fff;
  border: 1px solid #dce3eb;
  border-radius: 4px;
  margin-bottom: 12px;
}

.filter-form {
  flex: 1;
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 0;
  margin-right: 12px;
}

.action-group {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* 表格区 */
.table-panel {
  background: #fff;
  border: 1px solid #dce3eb;
  border-radius: 4px;
  padding: 0;
  overflow: hidden;
}

.ledger-table {
  width: 100%;
}

.ledger-table :deep(.el-table__header th) {
  background: #f4f6f9;
  color: #4a5568;
  font-weight: 600;
}

.eq-status {
  display: inline-block;
  padding: 2px 8px;
  font-size: 12px;
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

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 14px 16px;
  border-top: 1px solid #eef1f5;
}
</style>
