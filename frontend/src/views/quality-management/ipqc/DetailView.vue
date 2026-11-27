<template>
  <div v-loading="loading" class="ipqc-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">IPQC 详情</h1>
        <p class="page-sub">检验记录主表 + 项目明细 · 数据来自品质检验记录</p>
      </div>
      <div class="actions">
        <el-button
          v-if="row && !(row.item_results && row.item_results.length)"
          :loading="generating"
          @click="generateItems"
        >
          按模板生成明细
        </el-button>
        <el-button v-if="row" type="primary" @click="$router.push(`/quality-management/ipqc/edit/${row.id}`)">修改</el-button>
        <el-button @click="$router.push('/quality-management/inspection-records')">返回记录</el-button>
      </div>
    </header>

    <template v-if="row">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="检验单号">{{ row.inspection_no }}</el-descriptions-item>
        <el-descriptions-item label="录入类型">{{ entryLabel(row.ipqc_entry_type) }}</el-descriptions-item>
        <el-descriptions-item label="结果">{{ resultLabel(row.inspection_result) }}</el-descriptions-item>
        <el-descriptions-item label="工序">{{ row.process_name || row.process_id || '—' }}</el-descriptions-item>
        <el-descriptions-item label="模板">{{ row.template_id || '—' }}</el-descriptions-item>
        <el-descriptions-item label="检验人">{{ row.inspector }}</el-descriptions-item>
        <el-descriptions-item label="工单">{{ row.work_order_no || '—' }}</el-descriptions-item>
        <el-descriptions-item label="批次">{{ row.batch_no || '—' }}</el-descriptions-item>
        <el-descriptions-item label="料号">{{ row.product_code || row.material_code || '—' }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ row.customer_code || '—' }}</el-descriptions-item>
        <el-descriptions-item label="班次">{{ row.shift || '—' }}</el-descriptions-item>
        <el-descriptions-item label="抽检数">{{ row.inspected_qty ?? '—' }}</el-descriptions-item>
        <el-descriptions-item label="检验时间" :span="2">{{ formatDt(row.inspected_at) }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="3">{{ row.remark || '—' }}</el-descriptions-item>
      </el-descriptions>

      <div class="items-title">检验项目明细</div>
      <el-table :data="row.item_results || []" border>
        <el-table-column prop="item_code" label="编码" width="110" />
        <el-table-column prop="item_name" label="项目" min-width="140" />
        <el-table-column prop="standard_value" label="标准" min-width="120" />
        <el-table-column prop="actual_value" label="实测" min-width="120" />
        <el-table-column label="结果" width="100" align="center">
          <template #default="{ row: r }">{{ resultLabel(r.result) }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="120" />
      </el-table>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchIpqcRecord, generateIpqcRecordItems } from '../../../api/ipqc'

const route = useRoute()
const loading = ref(false)
const generating = ref(false)
const row = ref(null)

function entryLabel(v) {
  return { first_article: '首件', patrol: '巡检', reinspect: '复检', submit: '送检', import: '导入' }[v] || v || '—'
}
function resultLabel(v) {
  return { pass: '合格', fail: '不合格', pending: '待判' }[v] || v || '—'
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
    row.value = await fetchIpqcRecord(Number(route.params.id))
  } catch (e) {
    ElMessage.error(e.message || '加载详情失败')
  } finally {
    loading.value = false
  }
}

async function generateItems() {
  generating.value = true
  try {
    row.value = await generateIpqcRecordItems(Number(route.params.id))
    ElMessage.success('已生成检验明细')
  } catch (e) {
    ElMessage.error(e.message || '生成失败')
  } finally {
    generating.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.ipqc-page { display: flex; flex-direction: column; gap: 14px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.page-title { margin: 0; font-size: 20px; font-weight: 600; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: #6b7280; }
.items-title { margin-top: 8px; font-weight: 600; }
.actions { display: flex; gap: 8px; }
</style>
