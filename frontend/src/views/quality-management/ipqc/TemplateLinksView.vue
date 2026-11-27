<template>
  <div class="ipqc-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">模板关联</h1>
        <p class="page-sub">维护模板与检验项目的绑定关系 · 保存后自动写入升级记录</p>
      </div>
    </header>

    <section class="filter-bar">
      <el-select v-model="templateId" filterable placeholder="选择模板" style="width: 360px" @change="loadTemplate">
        <el-option
          v-for="t in templates"
          :key="t.id"
          :label="`${t.name} / ${t.template_code} / ${t.process_name || '—'}`"
          :value="t.id"
        />
      </el-select>
      <el-button type="primary" :disabled="!templateId" :loading="saving" @click="save">保存关联</el-button>
    </section>

    <el-alert
      v-if="current"
      :title="`当前版本 v${current.version} · 工序 ${current.process_name || '—'} · 已选 ${selectedIds.length} 项`"
      type="info"
      :closable="false"
      show-icon
      class="mb"
    />

    <el-transfer
      v-model="selectedIds"
      filterable
      :data="transferData"
      :titles="['可选项目', '已关联']"
      :props="{ key: 'id', label: 'label' }"
      style="width: 100%"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchIpqcTemplate,
  fetchIpqcTemplates,
  fetchIpqcTestItems,
  updateIpqcTemplate,
} from '../../../api/ipqc'

const templates = ref([])
const allItems = ref([])
const templateId = ref(null)
const current = ref(null)
const selectedIds = ref([])
const saving = ref(false)

const transferData = computed(() =>
  allItems.value.map((i) => ({
    id: i.id,
    label: `${i.item_code} · ${i.item_name}${i.process_name ? `（${i.process_name}）` : ''}`,
  })),
)

async function load() {
  const [tpl, items] = await Promise.all([
    fetchIpqcTemplates({ page: 1, pageSize: 100, status: 'active' }),
    fetchIpqcTestItems({ page: 1, pageSize: 100, status: 'active' }),
  ])
  templates.value = tpl.items || []
  allItems.value = items.items || []
  if (!templateId.value && templates.value.length) {
    templateId.value = templates.value[0].id
    await loadTemplate(templateId.value)
  }
}

async function loadTemplate(id) {
  if (!id) return
  current.value = await fetchIpqcTemplate(id)
  selectedIds.value = (current.value.items || []).map((i) => i.test_item_id)
}

async function save() {
  if (!templateId.value) return
  saving.value = true
  try {
    await updateIpqcTemplate(templateId.value, {
      items: selectedIds.value.map((id, idx) => ({
        test_item_id: id,
        sort_order: idx + 1,
        required: true,
      })),
      change_note: '模板关联页调整检验项目',
    })
    ElMessage.success('关联已保存并升版')
    await loadTemplate(templateId.value)
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.ipqc-page { display: flex; flex-direction: column; gap: 14px; }
.page-title { margin: 0; font-size: 20px; font-weight: 600; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: #6b7280; }
.filter-bar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.mb { margin-bottom: 4px; }
:deep(.el-transfer) { display: flex; justify-content: flex-start; }
</style>
