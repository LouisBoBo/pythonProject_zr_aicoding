<template>
  <div class="pcb-ops-page">
    <el-alert
      v-if="mesBanner"
      :title="mesBanner.title"
      :type="mesBanner.type"
      :description="mesBanner.description"
      show-icon
      :closable="false"
      class="mes-alert"
    />

    <el-card shadow="never" class="search-card">
      <el-form inline class="search-form">
        <el-form-item label="趋势天数">
          <el-select v-model="days" style="width: 100px" @change="handleSearch">
            <el-option label="近 7 日" :value="7" />
            <el-option label="近 14 日" :value="14" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间窗（对齐后）">
          <span class="window-text">{{ alignedWindowLabel }}</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSearch">重发趋势查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <span class="table-title">近7日产出与工单趋势</span>
        <el-tag size="small" type="info">仅实际量与工时</el-tag>
      </div>
      <el-table v-loading="loading" :data="outputTrend" stripe border empty-text="暂无趋势数据">
        <el-table-column prop="stat_date" label="日期" width="120" />
        <el-table-column prop="work_order_count" label="工单数" width="90" align="right" />
        <el-table-column prop="plan_qty" label="计划产量" width="100" align="right" />
        <el-table-column prop="actual_qty" label="实际产量" width="100" align="right" />
        <el-table-column prop="work_hours" label="工时" width="100" align="right">
          <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <span class="table-title">在制10单核查</span>
      </div>
      <el-table v-loading="loading" :data="wipOrders" stripe border empty-text="暂无在制工单">
        <el-table-column prop="order_no" label="工单号" min-width="130" />
        <el-table-column prop="product_name" label="品名" min-width="140" />
        <el-table-column prop="current_process" label="工序" min-width="100" />
        <el-table-column prop="wip_quantity" label="在制数量" width="100" align="right" />
        <el-table-column prop="plan_quantity" label="计划数量" width="100" align="right" />
        <el-table-column prop="actual_quantity" label="实际数量" width="100" align="right" />
        <el-table-column prop="actual_work_hours" label="实际工时" width="100" align="right">
          <template #default="{ row }">{{ row.actual_work_hours != null ? formatHours(row.actual_work_hours) : '—' }}</template>
        </el-table-column>
        <el-table-column prop="check_result" label="核查结果" width="100" align="center" />
      </el-table>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <span class="table-title">异常三单核查</span>
      </div>
      <el-table v-loading="loading" :data="abnormalOrders" stripe border empty-text="暂无开放异常">
        <el-table-column prop="production_line" label="产线" min-width="110" />
        <el-table-column prop="process" label="工序" min-width="100" />
        <el-table-column prop="defect_type" label="缺陷类型" min-width="120" />
        <el-table-column prop="severity" label="严重程度" width="100" align="center" />
        <el-table-column prop="discovered_at" label="发现时间" min-width="160" />
        <el-table-column prop="check_result" label="核查结果" width="100" align="center" />
      </el-table>
    </el-card>

    <el-card shadow="never" class="table-card blind-card">
      <div class="table-toolbar">
        <span class="table-title">数据盲区（不补图）</span>
      </div>
      <ul class="blind-list">
        <li v-for="item in blindSpots" :key="item">{{ item }}</li>
      </ul>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchPcbProductionOpsReport } from '../../api/reports/pcbProductionOps.js'

const loading = ref(false)
const days = ref(7)
const mesStatus = ref(null)
const dataSource = ref('')
const timeWindow = ref(null)
const outputTrend = ref([])
const wipOrders = ref([])
const abnormalOrders = ref([])
const blindSpots = ref([])

const alignedWindowLabel = computed(() => {
  const w = timeWindow.value
  if (!w) return '—'
  return `${w.aligned_from} 至 ${w.aligned_to}（请求 ${w.requested_from} ～ ${w.requested_to}）`
})

const mesBanner = computed(() => {
  const m = mesStatus.value
  if (!m) return null
  const ok = m.mes_status === 'normal' && m.reachable
  return {
    type: ok ? 'success' : 'warning',
    title: ok ? `MES 正常（${m.base_url}）` : `MES 未就绪（${m.base_url}）`,
    description: [
      `mes_status: ${m.mes_status}`,
      m.message,
      dataSource.value ? `取数来源: ${dataSource.value}` : '',
    ]
      .filter(Boolean)
      .join(' · '),
  }
})

function formatHours(value) {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toFixed(1)
}

async function loadReport() {
  loading.value = true
  try {
    const resp = await fetchPcbProductionOpsReport({ days: days.value })
    mesStatus.value = resp.mes_status || null
    dataSource.value = resp.data_source || ''
    timeWindow.value = resp.time_window || null
    outputTrend.value = resp.output_trend || []
    wipOrders.value = resp.wip_orders || []
    abnormalOrders.value = resp.abnormal_orders || []
    blindSpots.value = resp.blind_spots || []
  } catch (err) {
    mesStatus.value = null
    outputTrend.value = []
    wipOrders.value = []
    abnormalOrders.value = []
    blindSpots.value = ['达产率', '稼动率', '工序良率', '库存时间戳', 'MES 取数失败']
    ElMessage.error(err.message || 'zr_esc_mes_query 取数失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  loadReport()
}

onMounted(() => {
  loadReport()
})
</script>

<style scoped>
.pcb-ops-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mes-alert {
  border-radius: 8px;
}

.search-card,
.table-card {
  border-radius: 8px;
}

.search-form {
  margin-bottom: 0;
}

.window-text {
  font-size: 13px;
  color: #606266;
}

.table-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.table-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.blind-list {
  margin: 0;
  padding-left: 20px;
  color: #606266;
  line-height: 1.8;
}
</style>
