<template>
  <div class="inspection-records">
    <div class="page-banner">
      <div class="banner-icon">📋</div>
      <div>
        <h2 class="banner-title">点检记录</h2>
        <p class="banner-desc">查询历史点检结果，支持按设备、日期与状态筛选</p>
      </div>
    </div>

    <div class="filter-bar">
      <el-input
        v-model="filters.search"
        placeholder="设备名称 / 编号"
        clearable
        class="filter-input"
        @keyup.enter="handleSearch"
      />
      <el-date-picker
        v-model="filters.dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        class="filter-date"
      />
      <el-select v-model="filters.status" placeholder="点检结果" clearable class="filter-select">
        <el-option label="正常" value="normal" />
        <el-option label="异常" value="abnormal" />
        <el-option label="未完成" value="incomplete" />
        <el-option label="草稿" value="draft" />
      </el-select>
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="handleReset">重置</el-button>
    </div>

    <div class="table-wrap">
      <el-table v-loading="loading" :data="records" stripe border>
        <el-table-column prop="device_code" label="设备编码" min-width="120" />
        <el-table-column prop="device_name" label="设备名称" min-width="140" />
        <el-table-column prop="inspect_date" label="点检日期" width="120" />
        <el-table-column prop="inspector" label="点检人" width="100" />
        <el-table-column label="结果状态" width="100" align="center">
          <template #default="{ row }">
            <span class="status-tag" :class="'status-' + row.status">
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row)">查看详情</el-button>
            <el-button
              v-if="row.status === 'draft' || row.status === 'incomplete'"
              link
              type="warning"
              size="small"
              @click="openEdit(row)"
            >
              编辑
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="loadRecords"
          @current-change="loadRecords"
        />
      </div>
    </div>

    <el-dialog v-model="detailVisible" title="点检详情" width="640px" destroy-on-close>
      <template v-if="currentRecord">
        <div class="detail-header">
          <span>{{ currentRecord.device_code }} · {{ currentRecord.device_name }}</span>
          <span class="status-tag" :class="'status-' + currentRecord.status">
            {{ statusLabel(currentRecord.status) }}
          </span>
        </div>
        <div class="detail-meta">
          <span>点检日期：{{ currentRecord.inspect_date }}</span>
          <span>点检人：{{ currentRecord.inspector }}</span>
          <span v-if="currentRecord.plan_name">计划：{{ currentRecord.plan_name }}</span>
        </div>
        <el-table :data="currentRecord.items" border size="small" class="detail-table">
          <el-table-column prop="item_name" label="检查项目" min-width="120" />
          <el-table-column prop="standard_value" label="标准值" width="100">
            <template #default="{ row }">{{ row.standard_value || '-' }}</template>
          </el-table-column>
          <el-table-column prop="actual_value" label="实测值" width="90">
            <template #default="{ row }">{{ row.actual_value || '-' }}</template>
          </el-table-column>
          <el-table-column label="结果" width="70" align="center">
            <template #default="{ row }">
              <span v-if="row.result === 'OK'" class="result-ok">OK</span>
              <span v-else-if="row.result === 'NG'" class="result-ng">NG</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="100">
            <template #default="{ row }">{{ row.remark || '-' }}</template>
          </el-table-column>
        </el-table>
        <p v-if="currentRecord.remark" class="detail-remark">整体备注：{{ currentRecord.remark }}</p>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑点检记录" width="680px" destroy-on-close @closed="resetEdit">
      <el-form v-if="editForm" label-width="90px">
        <el-form-item label="点检人">
          <el-input v-model="editForm.inspector" />
        </el-form-item>
        <el-form-item label="点检日期">
          <el-date-picker v-model="editForm.inspect_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="整体备注">
          <el-input v-model="editForm.remark" type="textarea" :rows="2" />
        </el-form-item>
        <div v-for="(item, idx) in editForm.items" :key="idx" class="edit-item-row">
          <span class="edit-item-name">{{ item.item_name }}</span>
          <span class="edit-item-std">标准：{{ item.standard_value || '-' }}</span>
          <el-input v-model="item.actual_value" placeholder="实测值" size="small" style="width: 90px" />
          <el-radio-group v-model="item.result" size="small">
            <el-radio-button value="OK">OK</el-radio-button>
            <el-radio-button value="NG">NG</el-radio-button>
          </el-radio-group>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchInspectionRecord,
  fetchInspectionRecords,
  updateInspectionRecord,
} from '../../api/inspection'

const route = useRoute()
const loading = ref(false)
const saving = ref(false)
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

const filters = reactive({
  search: '',
  status: '',
  dateRange: null,
})

const detailVisible = ref(false)
const editVisible = ref(false)
const currentRecord = ref(null)
const editForm = ref(null)
const editingId = ref(null)

function statusLabel(status) {
  const map = { normal: '正常', abnormal: '异常', incomplete: '未完成', draft: '草稿' }
  return map[status] || status
}

async function loadRecords() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      pageSize: pageSize.value,
      search: filters.search || undefined,
      status: filters.status || undefined,
    }
    if (filters.dateRange?.length === 2) {
      params.dateFrom = filters.dateRange[0]
      params.dateTo = filters.dateRange[1]
    }
    const data = await fetchInspectionRecords(params)
    records.value = data.items
    total.value = data.total
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadRecords()
}

function handleReset() {
  filters.search = ''
  filters.status = ''
  filters.dateRange = null
  page.value = 1
  loadRecords()
}

async function openDetail(row) {
  try {
    currentRecord.value = await fetchInspectionRecord(row.id)
    detailVisible.value = true
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function openEdit(row) {
  try {
    const record = await fetchInspectionRecord(row.id)
    editingId.value = record.id
    editForm.value = {
      inspector: record.inspector,
      inspect_date: record.inspect_date,
      remark: record.remark || '',
      items: record.items.map((i) => ({ ...i })),
    }
    editVisible.value = true
  } catch (e) {
    ElMessage.error(e.message)
  }
}

function resetEdit() {
  editForm.value = null
  editingId.value = null
}

async function saveEdit() {
  saving.value = true
  try {
    await updateInspectionRecord(editingId.value, {
      inspector: editForm.value.inspector,
      inspect_date: editForm.value.inspect_date,
      remark: editForm.value.remark,
      items: editForm.value.items.map((i) => ({
        item_name: i.item_name,
        standard_value: i.standard_value,
        actual_value: i.actual_value,
        result: i.result,
        remark: i.remark,
      })),
      status: 'normal',
    })
    ElMessage.success('保存成功')
    editVisible.value = false
    loadRecords()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

watch(
  () => route.query,
  (q) => {
    if (q.status) filters.status = q.status
    if (q.detail) {
      openDetail({ id: Number(q.detail) })
    }
  },
  { immediate: true },
)

onMounted(loadRecords)
</script>

<style scoped>
.inspection-records {
  max-width: 1200px;
}

.page-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f0f5ff 0%, #fff 100%);
  border-left: 4px solid #409eff;
  border-radius: 0 6px 6px 0;
}

.banner-icon {
  font-size: 28px;
}

.banner-title {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.banner-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: #909399;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  padding: 16px 20px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 16px;
}

.filter-input {
  width: 200px;
}

.filter-date {
  width: 260px;
}

.filter-select {
  width: 130px;
}

.table-wrap {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 16px 20px;
}

.status-tag {
  display: inline-block;
  padding: 2px 10px;
  font-size: 12px;
  border-radius: 2px;
  font-weight: 500;
}

.status-normal {
  background: #f0f9eb;
  color: #67c23a;
}

.status-abnormal {
  background: #fef0f0;
  color: #f56c6c;
}

.status-incomplete {
  background: #fdf6ec;
  color: #e6a23c;
}

.status-draft {
  background: #f4f4f5;
  color: #909399;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-weight: 500;
}

.detail-meta {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: #606266;
  margin-bottom: 16px;
}

.detail-table {
  margin-bottom: 12px;
}

.detail-remark {
  font-size: 13px;
  color: #606266;
  margin: 0;
}

.result-ok {
  color: #67c23a;
  font-weight: 600;
}

.result-ng {
  color: #f56c6c;
  font-weight: 600;
}

.edit-item-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.edit-item-name {
  flex: 1;
  font-size: 13px;
}

.edit-item-std {
  font-size: 12px;
  color: #909399;
  width: 120px;
}
</style>
