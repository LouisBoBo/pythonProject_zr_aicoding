<template>
  <div class="master-page">
    <el-card shadow="never" class="search-card">
      <div class="page-heading">
        <h2 class="page-title">物料列表</h2>
        <p class="page-desc">维护物料主数据：编码、名称、分类、规格与库存阈值</p>
      </div>
      <el-form :model="filters" inline class="search-form" @submit.prevent="handleSearch">
        <el-form-item label="物料编码">
          <el-input
            v-model="filters.materialCode"
            placeholder="请输入物料编码"
            clearable
            style="width: 160px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="物料名称">
          <el-input
            v-model="filters.materialName"
            placeholder="请输入物料名称"
            clearable
            style="width: 160px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="分类">
          <el-input
            v-model="filters.category"
            placeholder="请输入分类"
            clearable
            style="width: 140px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <span class="table-title">物料</span>
        <div class="toolbar-right">
          <span v-if="total > 0" class="table-summary">共 {{ total }} 条</span>
          <el-button v-if="canWrite" type="primary" @click="openCreateDialog">新增物料</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
        <el-table-column prop="material_code" label="物料编码" min-width="130" />
        <el-table-column prop="material_name" label="物料名称" min-width="150" />
        <el-table-column prop="category" label="分类" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.category || '其他' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="spec" label="规格" min-width="120">
          <template #default="{ row }">{{ row.spec || '-' }}</template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="80" align="center" />
        <el-table-column prop="safety_stock" label="安全库存" width="100" align="right" />
        <el-table-column prop="max_stock" label="最大库存" width="100" align="right" />
        <el-table-column prop="supplier_name" label="供应商" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.supplier_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" :width="canWrite ? 140 : 60" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canWrite" link type="primary" size="small" @click="openEditDialog(row)">
              编辑
            </el-button>
            <el-button v-if="canWrite" link type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无物料数据" />
        </template>
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
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑物料' : '新增物料'"
      width="520px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="物料编码" prop="material_code">
          <el-input v-model="form.material_code" placeholder="唯一编码" maxlength="50" />
        </el-form-item>
        <el-form-item label="物料名称" prop="material_name">
          <el-input v-model="form.material_name" placeholder="物料名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-input v-model="form.category" placeholder="如：原材料、辅料" maxlength="50" />
        </el-form-item>
        <el-form-item label="规格" prop="spec">
          <el-input v-model="form.spec" placeholder="规格型号" maxlength="100" />
        </el-form-item>
        <el-form-item label="单位" prop="unit">
          <el-input v-model="form.unit" placeholder="件、kg 等" maxlength="20" />
        </el-form-item>
        <el-form-item label="安全库存" prop="safety_stock">
          <el-input-number v-model="form.safety_stock" :min="0" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="最大库存" prop="max_stock">
          <el-input-number v-model="form.max_stock" :min="0" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="供应商" prop="supplier_name">
          <el-input v-model="form.supplier_name" placeholder="选填" maxlength="100" />
        </el-form-item>
        <el-form-item label="采购单价" prop="purchase_price">
          <el-input-number
            v-model="form.purchase_price"
            :min="0"
            :precision="2"
            :step="0.01"
            style="width: 100%"
            controls-position="right"
          />
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
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePermissions } from '../../composables/usePermissions'
import {
  createMaterial,
  deleteMaterial,
  fetchMaterialList,
  updateMaterial,
} from '../../api/materials'

const route = useRoute()
const { can } = usePermissions()
const canWrite = computed(() => can('inventory.write'))

const filters = reactive({
  materialCode: '',
  materialName: '',
  category: '',
})

const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formRef = ref(null)

const defaultForm = () => ({
  material_code: '',
  material_name: '',
  category: '其他',
  spec: '',
  unit: '件',
  safety_stock: 0,
  max_stock: 0,
  supplier_name: '',
  purchase_price: null,
})

const form = reactive(defaultForm())

const formRules = {
  material_code: [{ required: true, message: '请输入物料编码', trigger: 'blur' }],
  material_name: [{ required: true, message: '请输入物料名称', trigger: 'blur' }],
  unit: [{ required: true, message: '请输入单位', trigger: 'blur' }],
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchMaterialList({
      page: page.value,
      pageSize: pageSize.value,
      materialCode: filters.materialCode || undefined,
      materialName: filters.materialName || undefined,
      category: filters.category || undefined,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err) {
    items.value = []
    total.value = 0
    const msg = err.message || ''
    if (msg === 'Not Found' || msg.includes('Not Found')) {
      ElMessage.error('物料列表接口未生效，请重启后端服务（端口 8009）后刷新页面')
    } else {
      ElMessage.error(msg || '加载物料列表失败')
    }
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.materialCode = ''
  filters.materialName = ''
  filters.category = ''
  page.value = 1
  loadList()
}

function resetForm() {
  Object.assign(form, defaultForm())
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
  Object.assign(form, {
    material_code: row.material_code,
    material_name: row.material_name,
    category: row.category || '其他',
    spec: row.spec || '',
    unit: row.unit || '件',
    safety_stock: row.safety_stock ?? 0,
    max_stock: row.max_stock ?? 0,
    supplier_name: row.supplier_name || '',
    purchase_price: row.purchase_price != null ? Number(row.purchase_price) : null,
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  submitting.value = true
  const payload = {
    material_code: form.material_code.trim(),
    material_name: form.material_name.trim(),
    category: (form.category || '其他').trim(),
    spec: form.spec?.trim() || null,
    unit: form.unit.trim(),
    safety_stock: form.safety_stock ?? 0,
    max_stock: form.max_stock ?? 0,
    supplier_name: form.supplier_name?.trim() || null,
    purchase_price: form.purchase_price != null ? form.purchase_price : null,
  }
  try {
    if (isEdit.value && editingId.value != null) {
      await updateMaterial(editingId.value, payload)
      ElMessage.success('已更新')
    } else {
      await createMaterial(payload)
      ElMessage.success('已新增')
    }
    dialogVisible.value = false
    await loadList()
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除物料「${row.material_name}」？`, '确认', {
      type: 'warning',
    })
    await deleteMaterial(row.id)
    ElMessage.success('已删除')
    await loadList()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.message || '删除失败')
  }
}

onMounted(async () => {
  const qCode =
    typeof route.query.materialCode === 'string' ? route.query.materialCode.trim() : ''
  if (qCode) {
    filters.materialCode = qCode
  }
  await loadList()
})
</script>

<style scoped>
.master-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 100%;
}

.search-card,
.table-card {
  border-radius: 8px;
  border: 1px solid #e8ecf1;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.page-heading {
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.page-title {
  margin: 0 0 4px;
  font-size: 17px;
  font-weight: 600;
  color: #303133;
}

.page-desc {
  margin: 0;
  font-size: 13px;
  color: #909399;
}

.search-form {
  margin-bottom: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  align-items: center;
}

.search-form :deep(.el-form-item) {
  margin-bottom: 8px;
  margin-right: 12px;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.table-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.table-summary {
  font-size: 13px;
  color: #606266;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
