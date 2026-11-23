<template>
  <div class="ipqc-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">模板升级记录</h1>
        <p class="page-sub">IPQC 模板版本历史 · 替换关联项目时自动升版</p>
      </div>
    </header>

    <section class="filter-bar">
      <el-input v-model="templateId" placeholder="模板 ID" clearable style="width: 140px" />
      <el-input v-model="templateCode" placeholder="模板编码" clearable style="width: 180px" />
      <el-button type="primary" @click="load">查询</el-button>
    </section>

    <el-table v-loading="loading" :data="items" border>
      <el-table-column prop="template_id" label="模板ID" width="90" />
      <el-table-column prop="version" label="版本" width="80" align="center" />
      <el-table-column prop="change_note" label="变更说明" min-width="220" show-overflow-tooltip />
      <el-table-column prop="changed_by" label="操作人" width="110" />
      <el-table-column label="时间" width="170">
        <template #default="{ row }">{{ formatDt(row.changed_at) }}</template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchIpqcTemplateVersions } from '../../../api/ipqc'

const route = useRoute()
const loading = ref(false)
const items = ref([])
const templateId = ref(route.query.templateId ? String(route.query.templateId) : '')
const templateCode = ref('')

function formatDt(v) {
  if (!v) return '—'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return v
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function load() {
  loading.value = true
  try {
    const data = await fetchIpqcTemplateVersions({
      templateId: templateId.value || undefined,
      templateCode: templateCode.value || undefined,
    })
    items.value = data.items || []
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.ipqc-page { display: flex; flex-direction: column; gap: 14px; }
.page-title { margin: 0; font-size: 20px; font-weight: 600; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: #6b7280; }
.filter-bar { display: flex; gap: 8px; flex-wrap: wrap; }
</style>
