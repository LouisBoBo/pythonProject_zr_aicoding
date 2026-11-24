<template>
  <div v-loading="loading" class="copq-analysis">
    <header class="page-header">
      <div>
        <h1 class="page-title">客诉 / COPQ 金额</h1>
        <p class="page-sub">客户主数据 · 客诉台账 · 不良质量成本汇总</p>
      </div>
      <div class="header-actions">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="投诉起"
          end-placeholder="投诉止"
          value-format="YYYY-MM-DD"
          style="width: 260px"
        />
        <el-select
          v-model="filterCustomer"
          placeholder="全部客户"
          clearable
          filterable
          style="width: 180px"
        >
          <el-option
            v-for="c in customers"
            :key="c.customer_code"
            :label="`${c.customer_name}（${c.customer_code}）`"
            :value="c.customer_code"
          />
        </el-select>
        <el-button type="primary" @click="loadData">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
        <el-button type="success" @click="openCreate">新建客诉</el-button>
      </div>
    </header>

    <section v-if="summary" class="summary-strip">
      <div class="sum-item">
        <span class="sum-label">客诉件数</span>
        <span class="sum-value">{{ summary.total_complaints.toLocaleString() }}</span>
      </div>
      <div class="sum-item">
        <span class="sum-label">COPQ 合计</span>
        <span class="sum-value bad">¥ {{ formatMoney(summary.total_copq_amount) }}</span>
      </div>
      <div class="sum-item">
        <span class="sum-label">未关闭</span>
        <span class="sum-value warn">{{ summary.open_count.toLocaleString() }}</span>
      </div>
      <div class="sum-item">
        <span class="sum-label">客户数</span>
        <span class="sum-value">{{ (summary.by_customer || []).length }}</span>
      </div>
    </section>

    <section class="chart-grid">
      <div class="chart-panel">
        <div class="panel-head">
          <span class="panel-title">按客户 COPQ</span>
        </div>
        <v-chart class="chart-box" :option="customerOption" autoresize />
      </div>
      <div class="chart-panel">
        <div class="panel-head">
          <span class="panel-title">按成本类别</span>
        </div>
        <v-chart class="chart-box" :option="categoryOption" autoresize />
      </div>
      <div class="chart-panel wide">
        <div class="panel-head">
          <span class="panel-title">COPQ 日趋势</span>
        </div>
        <v-chart class="chart-box" :option="trendOption" autoresize />
      </div>
    </section>

    <section class="table-panel">
      <div class="panel-head">
        <span class="panel-title">客诉明细</span>
        <span class="panel-hint">共 {{ listTotal }} 条</span>
      </div>
      <el-table :data="complaints" stripe border size="small" style="width: 100%">
        <el-table-column prop="complaint_no" label="单号" width="140" />
        <el-table-column prop="complaint_date" label="日期" width="110" />
        <el-table-column prop="customer_code" label="客户编码" width="100" />
        <el-table-column prop="customer_name" label="客户名称" min-width="140" />
        <el-table-column prop="complaint_type" label="类型" width="80" />
        <el-table-column prop="cost_category" label="成本类别" width="100">
          <template #default="{ row }">{{ categoryLabel(row.cost_category) }}</template>
        </el-table-column>
        <el-table-column prop="affected_qty" label="数量" width="80" align="right" />
        <el-table-column prop="unit_cost" label="单位成本" width="100" align="right">
          <template #default="{ row }">{{ formatMoney(row.unit_cost) }}</template>
        </el-table-column>
        <el-table-column prop="copq_amount" label="COPQ 金额" width="110" align="right">
          <template #default="{ row }">
            <span class="amount">{{ formatMoney(row.copq_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="product_name" label="产品" min-width="120" show-overflow-tooltip />
      </el-table>
      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="listTotal"
          layout="total, prev, pager, next"
          @current-change="loadComplaints"
        />
      </div>
    </section>

    <el-dialog v-model="createVisible" title="新建客诉" width="520px" destroy-on-close>
      <el-form :model="form" label-width="100px">
        <el-form-item label="客户" required>
          <el-select v-model="form.customer_code" filterable placeholder="选择客户" style="width: 100%">
            <el-option
              v-for="c in customers"
              :key="c.customer_code"
              :label="`${c.customer_name}（${c.customer_code}）`"
              :value="c.customer_code"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="投诉日期">
          <el-date-picker v-model="form.complaint_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.complaint_type" style="width: 100%">
            <el-option label="质量" value="质量" />
            <el-option label="交期" value="交期" />
            <el-option label="服务" value="服务" />
          </el-select>
        </el-form-item>
        <el-form-item label="成本类别">
          <el-select v-model="form.cost_category" style="width: 100%">
            <el-option label="索赔 claim" value="claim" />
            <el-option label="报废 scrap" value="scrap" />
            <el-option label="返工 rework" value="rework" />
            <el-option label="退货 return" value="return" />
          </el-select>
        </el-form-item>
        <el-form-item label="产品编码">
          <el-input v-model="form.product_code" />
        </el-form-item>
        <el-form-item label="产品名称">
          <el-input v-model="form.product_name" />
        </el-form-item>
        <el-form-item label="影响数量">
          <el-input-number v-model="form.affected_qty" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="单位成本">
          <el-input-number v-model="form.unit_cost" :min="0" :precision="4" style="width: 100%" />
        </el-form-item>
        <el-form-item label="严重度">
          <el-rate v-model="form.severity" :max="5" />
        </el-form-item>
        <el-form-item label="问题描述">
          <el-input v-model="form.problem_description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { createComplaint, fetchComplaints, fetchCopqSummary, fetchCustomers } from '../../api/copq'

use([CanvasRenderer, BarChart, LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent])

const CATEGORY_MAP = {
  claim: '索赔',
  scrap: '报废',
  rework: '返工',
  return: '退货',
}

const loading = ref(false)
const saving = ref(false)
const dateRange = ref(null)
const filterCustomer = ref('')
const customers = ref([])
const summary = ref(null)
const complaints = ref([])
const listTotal = ref(0)
const page = ref(1)
const pageSize = ref(10)
const createVisible = ref(false)
const form = ref(emptyForm())

function emptyForm() {
  return {
    customer_code: '',
    complaint_date: null,
    complaint_type: '质量',
    cost_category: 'claim',
    product_code: '',
    product_name: '',
    affected_qty: 0,
    unit_cost: 0,
    severity: 3,
    problem_description: '',
  }
}

function formatMoney(v) {
  const n = Number(v || 0)
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function categoryLabel(c) {
  return CATEGORY_MAP[c] || c
}

function statusLabel(s) {
  return { open: '新建', processing: '处理中', closed: '已关闭' }[s] || s
}

function statusTag(s) {
  return { open: 'danger', processing: 'warning', closed: 'success' }[s] || 'info'
}

async function loadCustomers() {
  const data = await fetchCustomers()
  customers.value = data.items || []
}

async function loadSummary() {
  const [dateFrom, dateTo] = dateRange.value || []
  summary.value = await fetchCopqSummary({ dateFrom, dateTo })
}

async function loadComplaints() {
  const [dateFrom, dateTo] = dateRange.value || []
  const data = await fetchComplaints({
    page: page.value,
    pageSize: pageSize.value,
    customerCode: filterCustomer.value || undefined,
    dateFrom,
    dateTo,
  })
  complaints.value = data.items || []
  listTotal.value = data.total || 0
}

async function loadData() {
  loading.value = true
  try {
    page.value = 1
    await Promise.all([loadSummary(), loadComplaints()])
  } catch (err) {
    ElMessage.error(err.message || '加载客诉/COPQ 失败')
  } finally {
    loading.value = false
  }
}

function handleReset() {
  dateRange.value = null
  filterCustomer.value = ''
  loadData()
}

function openCreate() {
  form.value = emptyForm()
  createVisible.value = true
}

async function submitCreate() {
  if (!form.value.customer_code) {
    ElMessage.warning('请选择客户')
    return
  }
  saving.value = true
  try {
    await createComplaint({ ...form.value })
    ElMessage.success('客诉已创建')
    createVisible.value = false
    await loadData()
  } catch (err) {
    ElMessage.error(err.message || '创建失败')
  } finally {
    saving.value = false
  }
}

const customerOption = computed(() => {
  const items = [...(summary.value?.by_customer || [])].reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 100, right: 40, top: 16, bottom: 24 },
    xAxis: { type: 'value', name: '元' },
    yAxis: {
      type: 'category',
      data: items.map((i) => i.customer_name || i.customer_code),
    },
    series: [
      {
        type: 'bar',
        data: items.map((i) => i.copq_amount),
        itemStyle: { color: '#dc2626' },
        barMaxWidth: 22,
        label: { show: true, position: 'right', formatter: (p) => formatMoney(p.value) },
      },
    ],
  }
})

const categoryOption = computed(() => {
  const items = summary.value?.by_category || []
  return {
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['35%', '65%'],
        data: items.map((i) => ({
          name: categoryLabel(i.cost_category),
          value: i.copq_amount,
        })),
      },
    ],
  }
})

const trendOption = computed(() => {
  const items = summary.value?.daily_trend || []
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['客诉件数', 'COPQ 金额'], top: 0 },
    grid: { left: 48, right: 56, top: 40, bottom: 40 },
    xAxis: {
      type: 'category',
      data: items.map((i) => String(i.date).slice(5)),
      axisLabel: { rotate: items.length > 14 ? 40 : 0 },
    },
    yAxis: [
      { type: 'value', name: '件数' },
      { type: 'value', name: '元', splitLine: { show: false } },
    ],
    series: [
      {
        name: '客诉件数',
        type: 'bar',
        data: items.map((i) => i.complaint_count),
        itemStyle: { color: '#93c5fd' },
        barMaxWidth: 28,
      },
      {
        name: 'COPQ 金额',
        type: 'line',
        yAxisIndex: 1,
        data: items.map((i) => i.copq_amount),
        smooth: true,
        itemStyle: { color: '#dc2626' },
      },
    ],
  }
})

onMounted(async () => {
  try {
    await loadCustomers()
  } catch {
    /* ignore */
  }
  await loadData()
})
</script>

<style scoped>
.copq-analysis {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 24px;
}
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
}
.page-sub {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}
.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.summary-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.sum-item {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.sum-label {
  color: #64748b;
  font-size: 12px;
}
.sum-value {
  font-size: 22px;
  font-weight: 650;
  color: #0f172a;
}
.sum-value.bad {
  color: #dc2626;
}
.sum-value.warn {
  color: #d97706;
}
.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.chart-panel,
.table-panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px 8px;
}
.chart-panel.wide {
  grid-column: 1 / -1;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 4px;
}
.panel-title {
  font-weight: 600;
  font-size: 14px;
}
.panel-hint {
  color: #94a3b8;
  font-size: 12px;
}
.chart-box {
  height: 280px;
  width: 100%;
}
.amount {
  color: #dc2626;
  font-weight: 600;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
@media (max-width: 960px) {
  .summary-strip,
  .chart-grid {
    grid-template-columns: 1fr;
  }
  .chart-panel.wide {
    grid-column: auto;
  }
}
</style>
