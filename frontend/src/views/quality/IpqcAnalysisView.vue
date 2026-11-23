<template>
  <div v-loading="loading" class="ipqc-analysis">
    <header class="page-header">
      <div>
        <h1 class="page-title">IPQC 检验分析</h1>
        <p class="page-sub">工序合格率 · 日不合格率 · 客户不合格 · 待审与审核时效</p>
      </div>
      <div class="header-actions">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="检验起"
          end-placeholder="检验止"
          value-format="YYYY-MM-DD"
          style="width: 260px"
        />
        <el-button type="primary" @click="loadData">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>
    </header>

    <section v-if="summary" class="summary-strip">
      <div class="sum-item">
        <span class="sum-label">检验单量</span>
        <span class="sum-value">{{ summary.total.toLocaleString() }}</span>
      </div>
      <div class="sum-item">
        <span class="sum-label">合格率</span>
        <span class="sum-value ok">{{ summary.pass_rate }}%</span>
      </div>
      <div class="sum-item">
        <span class="sum-label">不合格率</span>
        <span class="sum-value bad">{{ summary.fail_rate }}%</span>
      </div>
      <div class="sum-item">
        <span class="sum-label">待审积压</span>
        <span class="sum-value warn">{{ summary.pending_count.toLocaleString() }}</span>
      </div>
    </section>

    <section class="chart-grid">
      <div class="chart-panel">
        <div class="panel-head">
          <span class="panel-title">1. 工序合格率</span>
          <span class="panel-hint">成型 / 钻孔 / 阻焊</span>
        </div>
        <v-chart class="chart-box" :option="processOption" autoresize />
      </div>

      <div class="chart-panel">
        <div class="panel-head">
          <span class="panel-title">2. 日不合格率趋势</span>
          <span class="panel-hint">按检验日</span>
        </div>
        <v-chart class="chart-box" :option="dailyOption" autoresize />
      </div>

      <div class="chart-panel">
        <div class="panel-head">
          <span class="panel-title">3. 客户不合格 Top10</span>
          <span class="panel-hint">按不合格件数</span>
        </div>
        <v-chart class="chart-box" :option="customerOption" autoresize />
      </div>

      <div class="chart-panel">
        <div class="panel-head">
          <span class="panel-title">4. 待审积压 + 审核时效</span>
          <span class="panel-hint" v-if="checkLag">
            中位 {{ checkLag.median_hours ?? '—' }}h · &gt;24h 占比 {{ checkLag.over_24h_ratio }}%
          </span>
        </div>
        <div class="lag-meta" v-if="checkLag">
          <span>待审 {{ checkLag.pending_count }}</span>
          <span>已审 {{ checkLag.checked_count }}</span>
          <span>平均 {{ checkLag.avg_hours ?? '—' }}h</span>
          <span>P75 {{ checkLag.p75_hours ?? '—' }}h</span>
        </div>
        <v-chart class="chart-box lag-chart" :option="lagOption" autoresize />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
  MarkLineComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { fetchIpqcAnalytics } from '../../api/quality'

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  MarkLineComponent,
])

const loading = ref(false)
const dateRange = ref(null)
const summary = ref(null)
const processYield = ref([])
const dailyTrend = ref([])
const customerFailTop = ref([])
const checkLag = ref(null)

async function loadData() {
  loading.value = true
  try {
    const [dateFrom, dateTo] = dateRange.value || []
    const data = await fetchIpqcAnalytics({ dateFrom, dateTo, customerTop: 10 })
    summary.value = data.summary
    processYield.value = data.process_yield || []
    dailyTrend.value = data.daily_trend || []
    customerFailTop.value = data.customer_fail_top || []
    checkLag.value = data.check_lag
  } catch (err) {
    ElMessage.error(err.message || '加载 IPQC 分析失败')
  } finally {
    loading.value = false
  }
}

function handleReset() {
  dateRange.value = null
  loadData()
}

function processLabel(item) {
  const name = (item.process_name || '').trim()
  // 纯数字 ID 或空名：显示短别名，避免长 ID 挤掉相邻工序名
  if (!name || /^\d+$/.test(name)) {
    return '未知工序'
  }
  return name
}

const processOption = computed(() => {
  const items = processYield.value
  const names = items.map(processLabel)
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params) {
        const idx = params?.[0]?.dataIndex
        if (idx == null) return ''
        const row = items[idx]
        const title = processLabel(row)
        const idHint = row.process_id ? `<br/>ID: ${row.process_id}` : ''
        const lines = (params || [])
          .map((p) => `${p.marker}${p.seriesName}: ${p.value}`)
          .join('<br/>')
        return `${title}${idHint}<br/>${lines}<br/>合格 ${row.pass_count} / 不合格 ${row.fail_count} / 待审 ${row.pending_count}`
      },
    },
    legend: { data: ['合格率%', '不合格率%'], top: 0 },
    grid: { left: 48, right: 24, top: 40, bottom: 48 },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: {
        interval: 0, // 强制显示全部工序名（避免被长标签挤掉）
        hideOverlap: false,
        fontSize: 12,
      },
    },
    yAxis: { type: 'value', name: '%', max: 100 },
    series: [
      {
        name: '合格率%',
        type: 'bar',
        data: items.map((i) => i.pass_rate),
        itemStyle: { color: '#059669' },
        barMaxWidth: 36,
        label: { show: true, position: 'top', formatter: '{c}%' },
      },
      {
        name: '不合格率%',
        type: 'bar',
        data: items.map((i) => i.fail_rate),
        itemStyle: { color: '#dc2626' },
        barMaxWidth: 36,
        label: { show: true, position: 'top', formatter: '{c}%' },
      },
    ],
  }
})

const dailyOption = computed(() => {
  const items = dailyTrend.value
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['检验单量', '不合格率%'], top: 0 },
    grid: { left: 48, right: 48, top: 40, bottom: 40 },
    xAxis: {
      type: 'category',
      data: items.map((i) => i.date.slice(5)),
      axisLabel: { rotate: items.length > 14 ? 40 : 0 },
    },
    yAxis: [
      { type: 'value', name: '单量' },
      { type: 'value', name: '%', max: 100, splitLine: { show: false } },
    ],
    series: [
      {
        name: '检验单量',
        type: 'bar',
        data: items.map((i) => i.total),
        itemStyle: { color: '#93c5fd' },
        barMaxWidth: 28,
      },
      {
        name: '不合格率%',
        type: 'line',
        yAxisIndex: 1,
        data: items.map((i) => i.fail_rate),
        smooth: true,
        itemStyle: { color: '#dc2626' },
        lineStyle: { width: 2 },
      },
    ],
  }
})

const customerOption = computed(() => {
  const items = [...customerFailTop.value].reverse()
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params) {
        const p = params?.[0]
        if (!p) return ''
        const row = items[p.dataIndex]
        return `${row.customer_code}<br/>不合格 ${row.fail_count} / 合计 ${row.total}<br/>不合格率 ${row.fail_rate}%`
      },
    },
    grid: { left: 72, right: 48, top: 16, bottom: 24 },
    xAxis: { type: 'value', name: '不合格件数' },
    yAxis: {
      type: 'category',
      data: items.map((i) => i.customer_code),
    },
    series: [
      {
        type: 'bar',
        data: items.map((i) => i.fail_count),
        itemStyle: { color: '#f97316' },
        barMaxWidth: 22,
        label: { show: true, position: 'right' },
      },
    ],
  }
})

const lagOption = computed(() => {
  const buckets = checkLag.value?.buckets || []
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 48, right: 24, top: 24, bottom: 32 },
    xAxis: { type: 'category', data: buckets.map((b) => b.label) },
    yAxis: { type: 'value', name: '已审单量' },
    series: [
      {
        type: 'bar',
        data: buckets.map((b) => b.count),
        itemStyle: { color: '#6366f1' },
        barMaxWidth: 40,
        label: { show: true, position: 'top' },
      },
    ],
  }
})

onMounted(loadData)
</script>

<style scoped>
.ipqc-analysis {
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
  font-weight: 600;
  color: #111827;
}

.page-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.sum-item {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sum-label {
  font-size: 12px;
  color: #6b7280;
}

.sum-value {
  font-size: 22px;
  font-weight: 650;
  color: #111827;
}

.sum-value.ok {
  color: #059669;
}

.sum-value.bad {
  color: #dc2626;
}

.sum-value.warn {
  color: #d97706;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.chart-panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px 16px 8px;
  min-height: 340px;
  display: flex;
  flex-direction: column;
}

.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.panel-hint {
  font-size: 12px;
  color: #9ca3af;
}

.lag-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}

.chart-box {
  width: 100%;
  height: 280px;
}

.lag-chart {
  height: 250px;
}

@media (max-width: 960px) {
  .summary-strip,
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
