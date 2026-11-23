<template>
  <div class="ipqc-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">IPQC 记录修改</h1>
        <p class="page-sub">从检验记录中选择单据进入修改 · 与导入数据同一张表</p>
      </div>
    </header>

    <section class="filter-bar">
      <el-input v-model="filters.inspectionNo" placeholder="检验单号" clearable style="width: 150px" @keyup.enter="search" />
      <el-select v-model="filters.processName" placeholder="工序" clearable style="width: 120px">
        <el-option label="成型" value="成型" />
        <el-option label="钻孔" value="钻孔" />
        <el-option label="阻焊" value="阻焊" />
        <el-option label="待确认工序" value="待确认工序" />
      </el-select>
      <el-select v-model="filters.inspectionResult" placeholder="结果" clearable style="width: 110px">
        <el-option label="合格" value="pass" />
        <el-option label="不合格" value="fail" />
      </el-select>
      <el-select v-model="filters.ipqcEntryType" placeholder="录入类型" clearable style="width: 120px">
        <el-option label="导入" value="import" />
        <el-option label="首件" value="first_article" />
        <el-option label="巡检" value="patrol" />
        <el-option label="复检" value="reinspect" />
      </el-select>
      <el-button type="primary" @click="search">查询</el-button>
    </section>

    <el-table v-loading="loading" :data="items" border>
      <el-table-column prop="inspection_no" label="检验单号" min-width="150" />
      <el-table-column label="工序" width="110">
        <template #default="{ row }">{{ row.process_name || '—' }}</template>
      </el-table-column>
      <el-table-column label="结果" width="90" align="center">
        <template #default="{ row }">{{ resultLabel(row.inspection_result) }}</template>
      </el-table-column>
      <el-table-column label="录入类型" width="90" align="center">
        <template #default="{ row }">{{ entryLabel(row.ipqc_entry_type) }}</template>
      </el-table-column>
      <el-table-column prop="inspector" label="检验人" width="90" />
      <el-table-column label="检验时间" width="160">
        <template #default="{ row }">{{ formatDt(row.inspected_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/quality-management/ipqc/edit/${row.id}`)">修改</el-button>
          <el-button link @click="$router.push(`/quality-management/ipqc/detail/${row.id}`)">详情</el-button>
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
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchQualityInspectionRecords } from '../../../api/qualityInspectionRecords'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = reactive({
  inspectionNo: '',
  processName: '',
  inspectionResult: '',
  ipqcEntryType: '',
})

function resultLabel(v) {
  return { pass: '合格', fail: '不合格', pending: '待判' }[v] || v || '—'
}
function entryLabel(v) {
  return { import: '导入', first_article: '首件', patrol: '巡检', reinspect: '复检', submit: '送检' }[v] || v || '—'
}
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
    const data = await fetchQualityInspectionRecords({
      page: page.value,
      pageSize: pageSize.value,
      inspectionNo: filters.inspectionNo || undefined,
      processName: filters.processName || undefined,
      inspectionResult: filters.inspectionResult || undefined,
      ipqcEntryType: filters.ipqcEntryType || undefined,
      inspectionType: 'process',
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

onMounted(load)
</script>

<style scoped>
.ipqc-page { display: flex; flex-direction: column; gap: 14px; }
.page-title { margin: 0; font-size: 20px; font-weight: 600; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: #6b7280; }
.filter-bar { display: flex; flex-wrap: wrap; gap: 8px; }
.pager { display: flex; justify-content: flex-end; }
</style>
