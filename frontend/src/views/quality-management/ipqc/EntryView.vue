<template>
  <div class="ipqc-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">{{ title }}</h1>
        <p class="page-sub">写入品质检验记录（process）· 与导入/分析/任务同一数据源</p>
      </div>
    </header>

    <el-form :model="form" label-width="100px" class="entry-form">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="检验模板" required>
            <el-select
              v-model="form.template_id"
              filterable
              placeholder="选择模板"
              style="width: 100%"
              @change="onTemplateChange"
            >
              <el-option
                v-for="t in templates"
                :key="t.id"
                :label="`${t.name}（${t.template_code}）`"
                :value="t.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="工序">
            <el-input v-model="form.process_name" placeholder="自动带出，可改" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="工单号">
            <el-input v-model="form.work_order_no" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="批次号">
            <el-input v-model="form.batch_no" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="料号">
            <el-input v-model="form.product_code" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="客户">
            <el-input v-model="form.customer_code" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="班次">
            <el-select v-model="form.shift" clearable style="width: 100%">
              <el-option label="白班" value="白班" />
              <el-option label="晚班" value="晚班" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="抽检数">
            <el-input-number v-model="form.inspected_qty" :min="0" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col v-if="entryType !== 'submit'" :span="8">
          <el-form-item label="总结果">
            <el-select v-model="form.inspection_result" style="width: 100%">
              <el-option label="合格" value="pass" />
              <el-option label="不合格" value="fail" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="备注">
            <el-input v-model="form.remark" type="textarea" :rows="2" />
          </el-form-item>
        </el-col>
      </el-row>

      <div v-if="entryType !== 'submit'" class="items-block">
        <div class="items-title">检验项目明细</div>
        <el-table :data="form.item_results" border size="small">
          <el-table-column prop="item_name" label="项目" min-width="120" />
          <el-table-column prop="standard_value" label="标准" min-width="120" />
          <el-table-column label="实测" min-width="140">
            <template #default="{ row }">
              <el-input v-model="row.actual_value" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="结果" width="130">
            <template #default="{ row }">
              <el-select v-model="row.result" size="small" style="width: 110px">
                <el-option label="待判" value="pending" />
                <el-option label="合格" value="pass" />
                <el-option label="不合格" value="fail" />
              </el-select>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="actions">
        <el-button type="primary" :loading="saving" @click="submit">提交</el-button>
        <el-button @click="resetForm">清空</el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createIpqcRecord, fetchIpqcTemplate, fetchIpqcTemplates } from '../../../api/ipqc'

const props = defineProps({
  entryType: { type: String, default: '' },
})

const route = useRoute()
const router = useRouter()

const entryType = computed(() => {
  if (props.entryType) return props.entryType
  const map = {
    'ipqc-first-article': 'first_article',
    'ipqc-patrol': 'patrol',
    'ipqc-reinspect': 'reinspect',
    'ipqc-submit': 'submit',
  }
  for (const [key, val] of Object.entries(map)) {
    if (route.path.includes(key)) return val
  }
  return 'patrol'
})

const title = computed(() => {
  return (
    {
      first_article: 'IPQC 首件录入',
      patrol: 'IPQC 巡检录入',
      reinspect: '复检结果录入',
      submit: '送检提交',
    }[entryType.value] || 'IPQC 录入'
  )
})

const saving = ref(false)
const templates = ref([])
const form = reactive({
  template_id: null,
  process_id: '',
  process_name: '',
  work_order_no: '',
  batch_no: '',
  product_code: '',
  customer_code: '',
  shift: '白班',
  inspected_qty: 1,
  inspection_result: 'pass',
  remark: '',
  item_results: [],
})

async function loadTemplates() {
  const data = await fetchIpqcTemplates({ page: 1, pageSize: 100, status: 'active' })
  templates.value = data.items || []
}

async function onTemplateChange(id) {
  if (!id) return
  const tpl = await fetchIpqcTemplate(id)
  form.process_id = tpl.process_id || ''
  form.process_name = tpl.process_name || ''
  form.item_results = (tpl.items || []).map((i, idx) => ({
    test_item_id: i.test_item_id,
    item_code: i.item_code,
    item_name: i.item_name,
    standard_value: i.standard_value,
    actual_value: '',
    result: 'pending',
    sort_order: i.sort_order || idx + 1,
  }))
}

function resetForm() {
  form.template_id = null
  form.process_id = ''
  form.process_name = ''
  form.work_order_no = ''
  form.batch_no = ''
  form.product_code = ''
  form.customer_code = ''
  form.shift = '白班'
  form.inspected_qty = 1
  form.inspection_result = 'pass'
  form.remark = ''
  form.item_results = []
}

async function submit() {
  if (!form.template_id) {
    ElMessage.warning('请选择检验模板')
    return
  }
  saving.value = true
  try {
    const body = {
      entry_type: entryType.value,
      template_id: form.template_id,
      process_id: form.process_id || null,
      process_name: form.process_name || null,
      work_order_no: form.work_order_no || null,
      batch_no: form.batch_no || null,
      product_code: form.product_code || null,
      customer_code: form.customer_code || null,
      shift: form.shift || null,
      inspected_qty: form.inspected_qty,
      remark: form.remark || null,
      inspection_result: entryType.value === 'submit' ? 'pending' : form.inspection_result,
      item_results: entryType.value === 'submit' ? [] : form.item_results,
    }
    const row = await createIpqcRecord(body)
    ElMessage.success(`已提交：${row.inspection_no}`)
    resetForm()
    if (entryType.value === 'submit') {
      router.push('/quality-management/inspection-tasks')
    } else {
      router.push(`/quality-management/ipqc/detail/${row.id}`)
    }
  } catch (e) {
    ElMessage.error(e.message || '提交失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadTemplates)
</script>

<style scoped>
.ipqc-page { display: flex; flex-direction: column; gap: 14px; padding-bottom: 24px; }
.page-title { margin: 0; font-size: 20px; font-weight: 600; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: #6b7280; }
.entry-form {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 18px 18px 8px;
}
.items-block { margin: 8px 0 16px; }
.items-title { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
.actions { display: flex; gap: 8px; padding: 8px 0 16px 100px; }
</style>
