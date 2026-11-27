<template>
  <div v-loading="loading" class="ipqc-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">IPQC 记录修改</h1>
        <p class="page-sub">修改品质检验记录 · 可替换项目明细</p>
      </div>
    </header>

    <el-form v-if="form.id" :model="form" label-width="100px" class="entry-form">
      <el-form-item label="检验单号">
        <el-input :model-value="form.inspection_no" disabled />
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="工序">
            <el-input v-model="form.process_name" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="总结果">
            <el-select v-model="form.inspection_result" style="width: 100%">
              <el-option label="合格" value="pass" />
              <el-option label="不合格" value="fail" />
              <el-option label="待判" value="pending" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="工单号">
            <el-input v-model="form.work_order_no" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="批次">
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
        <el-col :span="24">
          <el-form-item label="备注">
            <el-input v-model="form.remark" type="textarea" :rows="2" />
          </el-form-item>
        </el-col>
      </el-row>

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

      <div class="actions">
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
        <el-button @click="$router.back()">取消</el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchIpqcRecord, updateIpqcRecord } from '../../../api/ipqc'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const form = reactive({
  id: null,
  inspection_no: '',
  process_name: '',
  inspection_result: 'pass',
  work_order_no: '',
  batch_no: '',
  product_code: '',
  customer_code: '',
  remark: '',
  item_results: [],
})

onMounted(async () => {
  loading.value = true
  try {
    const row = await fetchIpqcRecord(Number(route.params.id))
    Object.assign(form, {
      id: row.id,
      inspection_no: row.inspection_no,
      process_name: row.process_name || '',
      inspection_result: row.inspection_result,
      work_order_no: row.work_order_no || '',
      batch_no: row.batch_no || '',
      product_code: row.product_code || '',
      customer_code: row.customer_code || '',
      remark: row.remark || '',
      item_results: (row.item_results || []).map((i) => ({ ...i })),
    })
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
})

async function save() {
  saving.value = true
  try {
    await updateIpqcRecord(form.id, {
      process_name: form.process_name || null,
      inspection_result: form.inspection_result,
      work_order_no: form.work_order_no || null,
      batch_no: form.batch_no || null,
      product_code: form.product_code || null,
      customer_code: form.customer_code || null,
      remark: form.remark || null,
      item_results: form.item_results,
    })
    ElMessage.success('已保存')
    router.push(`/quality-management/ipqc/detail/${form.id}`)
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.ipqc-page { display: flex; flex-direction: column; gap: 14px; }
.page-title { margin: 0; font-size: 20px; font-weight: 600; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: #6b7280; }
.entry-form {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 18px;
}
.items-title { font-weight: 600; margin: 8px 0; }
.actions { margin-top: 16px; display: flex; gap: 8px; }
</style>
