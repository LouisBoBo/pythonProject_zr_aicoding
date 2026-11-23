<template>
  <div class="ipqc-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">IPQC 模板</h1>
        <p class="page-sub">检验模板主数据 · template_code 对齐源 CTEMPLATE_ID · 关联检验项目</p>
      </div>
      <el-button type="primary" @click="openCreate">新建模板</el-button>
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
      <el-table-column prop="template_code" label="模板编码" min-width="150" />
      <el-table-column prop="name" label="模板名称" min-width="160" />
      <el-table-column prop="process_name" label="工序" width="100">
        <template #default="{ row }">{{ row.process_name || '—' }}</template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="70" align="center" />
      <el-table-column label="项目数" width="80" align="center">
        <template #default="{ row }">{{ row.items?.length || 0 }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80" align="center">
        <template #default="{ row }">{{ row.status === 'active' ? '启用' : '停用' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑/关联</el-button>
          <el-button link @click="$router.push(`/quality-management/ipqc/template-versions?templateId=${row.id}`)">升级记录</el-button>
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

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑模板' : '新建模板'" width="720px" destroy-on-close>
      <el-form :model="form" label-width="96px">
        <el-form-item label="模板编码" required>
          <el-input v-model="form.template_code" :disabled="!!editingId" maxlength="40" />
        </el-form-item>
        <el-form-item label="模板名称" required>
          <el-input v-model="form.name" maxlength="100" />
        </el-form-item>
        <el-form-item label="工序名称">
          <el-input v-model="form.process_name" maxlength="50" placeholder="成型/钻孔/阻焊" />
        </el-form-item>
        <el-form-item label="工序 ID">
          <el-input v-model="form.process_id" maxlength="40" />
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
        <el-form-item v-if="editingId" label="升版说明">
          <el-input v-model="form.change_note" placeholder="替换关联项目时写入升级记录" />
        </el-form-item>
        <el-form-item label="关联项目">
          <div class="link-box">
            <el-select
              v-model="selectedItemIds"
              multiple
              filterable
              collapse-tags
              collapse-tags-tooltip
              placeholder="选择测试项目"
              style="width: 100%"
            >
              <el-option
                v-for="it in allItems"
                :key="it.id"
                :label="`${it.item_code} · ${it.item_name}`"
                :value="it.id"
              />
            </el-select>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createIpqcTemplate,
  fetchIpqcTemplates,
  fetchIpqcTestItems,
  updateIpqcTemplate,
} from '../../../api/ipqc'

const loading = ref(false)
const saving = ref(false)
const items = ref([])
const allItems = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = reactive({ keyword: '', processName: '', status: '' })
const dialogVisible = ref(false)
const editingId = ref(null)
const selectedItemIds = ref([])
const form = reactive({
  template_code: '',
  name: '',
  process_id: '',
  process_name: '',
  status: 'active',
  remark: '',
  change_note: '',
})

async function load() {
  loading.value = true
  try {
    const data = await fetchIpqcTemplates({
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

async function loadAllItems() {
  const data = await fetchIpqcTestItems({ page: 1, pageSize: 100, status: 'active' })
  allItems.value = data.items || []
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
    template_code: '',
    name: '',
    process_id: '',
    process_name: '',
    status: 'active',
    remark: '',
    change_note: '',
  })
  selectedItemIds.value = []
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, {
    template_code: row.template_code,
    name: row.name,
    process_id: row.process_id || '',
    process_name: row.process_name || '',
    status: row.status || 'active',
    remark: row.remark || '',
    change_note: '',
  })
  selectedItemIds.value = (row.items || []).map((i) => i.test_item_id)
  dialogVisible.value = true
}

async function save() {
  if (!form.template_code || !form.name) {
    ElMessage.warning('请填写模板编码和名称')
    return
  }
  saving.value = true
  try {
    const itemsPayload = selectedItemIds.value.map((id, idx) => ({
      test_item_id: id,
      sort_order: idx + 1,
      required: true,
    }))
    if (editingId.value) {
      await updateIpqcTemplate(editingId.value, {
        name: form.name,
        process_id: form.process_id || null,
        process_name: form.process_name || null,
        status: form.status,
        remark: form.remark || null,
        items: itemsPayload,
        change_note: form.change_note || null,
      })
    } else {
      await createIpqcTemplate({
        template_code: form.template_code,
        name: form.name,
        process_id: form.process_id || null,
        process_name: form.process_name || null,
        remark: form.remark || null,
        items: itemsPayload,
      })
    }
    ElMessage.success('已保存')
    dialogVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all([load(), loadAllItems()])
})
</script>

<style scoped>
.ipqc-page { display: flex; flex-direction: column; gap: 14px; padding-bottom: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.page-title { margin: 0; font-size: 20px; font-weight: 600; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: #6b7280; }
.filter-bar { display: flex; flex-wrap: wrap; gap: 8px; }
.pager { display: flex; justify-content: flex-end; }
.link-box { width: 100%; }
</style>
