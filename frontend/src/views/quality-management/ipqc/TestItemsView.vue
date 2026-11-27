<template>
  <div class="ipqc-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">{{ pageTitle }}</h1>
        <p class="page-sub">IPQC 检验项目主数据 · 供模板关联与录入明细使用</p>
      </div>
      <el-button type="primary" @click="openCreate">新建项目</el-button>
    </header>

    <section class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="编码/名称" clearable style="width: 180px" @keyup.enter="search" />
      <el-input v-model="filters.processName" placeholder="工序" clearable style="width: 120px" @keyup.enter="search" />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px">
        <el-option label="启用" value="active" />
        <el-option label="停用" value="disabled" />
      </el-select>
      <el-button type="primary" @click="search">查询</el-button>
      <el-button @click="reset">重置</el-button>
    </section>

    <el-table v-loading="loading" :data="items" border>
      <el-table-column prop="item_code" label="项目编码" min-width="120" />
      <el-table-column prop="item_name" label="项目名称" min-width="140" />
      <el-table-column prop="process_name" label="适用工序" width="100">
        <template #default="{ row }">{{ row.process_name || '通用' }}</template>
      </el-table-column>
      <el-table-column prop="standard_value" label="标准" min-width="140" show-overflow-tooltip />
      <el-table-column prop="judge_type" label="判定" width="90" align="center">
        <template #default="{ row }">{{ row.judge_type === 'numeric' ? '数值' : 'OK/NG' }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80" align="center">
        <template #default="{ row }">{{ row.status === 'active' ? '启用' : '停用' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        background
        @current-change="load"
      />
    </div>

    <el-dialog v-model="visible" :title="editingId ? '编辑项目' : '新建项目'" width="560px" destroy-on-close>
      <el-form :model="form" label-width="96px">
        <el-form-item label="项目编码" required>
          <el-input v-model="form.item_code" :disabled="!!editingId" maxlength="50" />
        </el-form-item>
        <el-form-item label="项目名称" required>
          <el-input v-model="form.item_name" maxlength="100" />
        </el-form-item>
        <el-form-item label="适用工序">
          <el-input v-model="form.process_name" placeholder="成型/钻孔/阻焊，空=通用" />
        </el-form-item>
        <el-form-item label="标准值">
          <el-input v-model="form.standard_value" />
        </el-form-item>
        <el-form-item label="判定类型">
          <el-select v-model="form.judge_type" style="width: 160px">
            <el-option label="OK/NG" value="ok_ng" />
            <el-option label="数值" value="numeric" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editingId" label="状态">
          <el-select v-model="form.status" style="width: 160px">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createIpqcTestItem, fetchIpqcTestItems, updateIpqcTestItem } from '../../../api/ipqc'

const route = useRoute()
const pageTitle = computed(() =>
  route.path.includes('item-query') ? '检验项目查询' : '测试项目',
)

const loading = ref(false)
const saving = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = reactive({ keyword: '', processName: '', status: '' })
const visible = ref(false)
const editingId = ref(null)
const form = reactive({
  item_code: '',
  item_name: '',
  process_name: '',
  standard_value: '',
  judge_type: 'ok_ng',
  status: 'active',
  remark: '',
})

async function load() {
  loading.value = true
  try {
    const data = await fetchIpqcTestItems({
      page: page.value,
      pageSize: pageSize.value,
      keyword: filters.keyword || undefined,
      processName: filters.processName || undefined,
      status: filters.status || undefined,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function reset() {
  filters.keyword = ''
  filters.processName = ''
  filters.status = ''
  search()
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    item_code: '',
    item_name: '',
    process_name: '',
    standard_value: '',
    judge_type: 'ok_ng',
    status: 'active',
    remark: '',
  })
  visible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, {
    item_code: row.item_code,
    item_name: row.item_name,
    process_name: row.process_name || '',
    standard_value: row.standard_value || '',
    judge_type: row.judge_type || 'ok_ng',
    status: row.status || 'active',
    remark: row.remark || '',
  })
  visible.value = true
}

async function save() {
  if (!form.item_code || !form.item_name) {
    ElMessage.warning('请填写编码和名称')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateIpqcTestItem(editingId.value, {
        item_name: form.item_name,
        process_name: form.process_name || null,
        standard_value: form.standard_value || null,
        judge_type: form.judge_type,
        status: form.status,
        remark: form.remark || null,
      })
    } else {
      await createIpqcTestItem({
        item_code: form.item_code,
        item_name: form.item_name,
        process_name: form.process_name || null,
        standard_value: form.standard_value || null,
        judge_type: form.judge_type,
        remark: form.remark || null,
      })
    }
    ElMessage.success('已保存')
    visible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.ipqc-page { display: flex; flex-direction: column; gap: 14px; padding-bottom: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.page-title { margin: 0; font-size: 20px; font-weight: 600; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: #6b7280; }
.filter-bar { display: flex; flex-wrap: wrap; gap: 8px; }
.pager { display: flex; justify-content: flex-end; }
</style>
