<template>
  <div v-loading="loading" class="spc-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">SPC 控制图</h1>
        <p class="page-sub">过程控制限 · 规格限 · Cp/Cpk · 失控点标记</p>
      </div>
      <div class="header-actions">
        <el-select v-model="filters.processName" placeholder="全部工序" clearable style="width: 140px">
          <el-option v-for="p in processOptions" :key="p" :label="p" :value="p" />
        </el-select>
        <el-select v-model="filters.characteristic" placeholder="全部特性" clearable style="width: 140px">
          <el-option v-for="c in charOptions" :key="c" :label="c" :value="c" />
        </el-select>
        <el-select v-model="filters.chartType" placeholder="全部图类型" clearable style="width: 130px">
          <el-option v-for="t in typeOptions" :key="t" :label="t" :value="t" />
        </el-select>
        <el-button type="primary" @click="loadList">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>
    </header>

    <section class="layout">
      <aside class="chart-list">
        <div class="panel-head">
          <span class="panel-title">控制图列表</span>
          <span class="panel-hint">{{ charts.length }}</span>
        </div>
        <div
          v-for="c in charts"
          :key="c.id"
          class="chart-item"
          :class="{ active: selectedId === c.id }"
          @click="selectChart(c.id)"
        >
          <div class="item-title">{{ c.chart_name }}</div>
          <div class="item-meta">
            {{ c.process_name }} · {{ c.characteristic }} · {{ c.chart_type }}
          </div>
          <div class="item-foot">
            <el-tag :type="c.status === 'alert' ? 'danger' : 'success'" size="small">
              {{ c.status === 'alert' ? '失控' : '正常' }}
            </el-tag>
            <span v-if="c.cpk != null">Cpk {{ c.cpk }}</span>
            <span>{{ c.sample_count }} 点</span>
          </div>
        </div>
        <el-empty v-if="!charts.length" description="暂无控制图" :image-size="64" />
      </aside>

      <main class="chart-detail" v-if="detail">
        <div class="panel-head">
          <div>
            <span class="panel-title">{{ detail.chart_name }}</span>
            <span class="panel-hint">
              {{ detail.process_name }} / {{ detail.characteristic }}
              <template v-if="detail.unit">（{{ detail.unit }}）</template>
            </span>
          </div>
          <el-button size="small" @click="recompute">重新计算</el-button>
        </div>

        <div class="kpi-row">
          <div class="kpi"><span>UCL</span><b>{{ fmt(detail.ucl) }}</b></div>
          <div class="kpi"><span>CL</span><b>{{ fmt(detail.cl) }}</b></div>
          <div class="kpi"><span>LCL</span><b>{{ fmt(detail.lcl) }}</b></div>
          <div class="kpi"><span>USL</span><b>{{ fmt(detail.usl) }}</b></div>
          <div class="kpi"><span>LSL</span><b>{{ fmt(detail.lsl) }}</b></div>
          <div class="kpi"><span>Cp</span><b>{{ fmt(detail.cp) }}</b></div>
          <div class="kpi"><span>Cpk</span><b :class="{ bad: detail.cpk != null && detail.cpk < 1.33 }">{{ fmt(detail.cpk) }}</b></div>
          <div class="kpi">
            <span>状态</span>
            <b :class="detail.status === 'alert' ? 'bad' : 'ok'">
              {{ detail.status === 'alert' ? '失控' : '正常' }}
            </b>
          </div>
        </div>

        <v-chart class="spc-chart" :option="chartOption" autoresize />

        <div v-if="detail.out_of_control_indexes?.length" class="alert-box">
          失控点序号：{{ detail.out_of_control_indexes.join('、') }}
        </div>
      </main>
      <main v-else class="chart-detail empty">
        <el-empty description="请选择左侧控制图" />
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, ScatterChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import {
  fetchSpcChartDetail,
  fetchSpcCharts,
  fetchSpcFilters,
  recomputeSpcChart,
} from '../../api/spc'

use([
  CanvasRenderer,
  LineChart,
  ScatterChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  MarkLineComponent,
])

const loading = ref(false)
const filters = ref({ processName: '', characteristic: '', chartType: '' })
const processOptions = ref([])
const charOptions = ref([])
const typeOptions = ref(['I-MR', 'Xbar-R'])
const charts = ref([])
const selectedId = ref(null)
const detail = ref(null)

function fmt(v) {
  if (v == null || Number.isNaN(Number(v))) return '—'
  return Number(Number(v).toFixed(4)).toString()
}

async function loadFilters() {
  const data = await fetchSpcFilters()
  processOptions.value = data.process_names || []
  charOptions.value = data.characteristics || []
  typeOptions.value = data.chart_types?.length ? data.chart_types : ['I-MR', 'Xbar-R']
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchSpcCharts({
      processName: filters.value.processName || undefined,
      characteristic: filters.value.characteristic || undefined,
      chartType: filters.value.chartType || undefined,
    })
    charts.value = data.items || []
    if (!charts.value.length) {
      selectedId.value = null
      detail.value = null
      return
    }
    const keep = charts.value.find((c) => c.id === selectedId.value)
    await selectChart(keep ? keep.id : charts.value[0].id)
  } catch (err) {
    ElMessage.error(err.message || '加载 SPC 列表失败')
  } finally {
    loading.value = false
  }
}

function syncListFromDetail(id) {
  const row = charts.value.find((c) => c.id === id)
  if (row && detail.value) {
    row.status = detail.value.status
    row.cpk = detail.value.cpk
    row.cp = detail.value.cp
    row.ucl = detail.value.ucl
    row.cl = detail.value.cl
    row.lcl = detail.value.lcl
    row.sample_count = detail.value.sample_count
  }
}

async function selectChart(id) {
  selectedId.value = id
  loading.value = true
  try {
    detail.value = await fetchSpcChartDetail(id)
    syncListFromDetail(id)
  } catch (err) {
    ElMessage.error(err.message || '加载控制图详情失败')
  } finally {
    loading.value = false
  }
}

async function recompute() {
  if (!selectedId.value) return
  loading.value = true
  try {
    detail.value = await recomputeSpcChart(selectedId.value)
    syncListFromDetail(selectedId.value)
    ElMessage.success('已重新计算控制限')
  } catch (err) {
    ElMessage.error(err.message || '重新计算失败')
  } finally {
    loading.value = false
  }
}

function handleReset() {
  filters.value = { processName: '', characteristic: '', chartType: '' }
  loadList()
}

const chartOption = computed(() => {
  const d = detail.value
  if (!d) return {}
  const points = d.points || []
  const xs = points.map((p) => p.index)
  const ys = points.map((p) => p.value)
  const markLines = []
  const pushLine = (y, name, color, dash) => {
    if (y == null) return
    markLines.push({
      yAxis: y,
      name,
      lineStyle: { color, type: dash || 'solid', width: name.includes('规格') ? 1.5 : 1.5 },
      label: { formatter: name, position: 'insideEndTop', color },
    })
  }
  pushLine(d.ucl, 'UCL', '#dc2626', 'dashed')
  pushLine(d.cl, 'CL', '#2563eb', 'solid')
  pushLine(d.lcl, 'LCL', '#dc2626', 'dashed')
  pushLine(d.usl, 'USL 规格', '#9333ea', 'dotted')
  pushLine(d.lsl, 'LSL 规格', '#9333ea', 'dotted')

  const ooc = points.filter((p) => p.out_of_control)

  return {
    tooltip: {
      trigger: 'axis',
      formatter(params) {
        const p = params?.[0]
        if (!p) return ''
        const row = points[p.dataIndex]
        const flag = row?.out_of_control ? '（失控）' : ''
        return `#${row?.index}${flag}<br/>值：${row?.value}`
      },
    },
    grid: { left: 56, right: 72, top: 32, bottom: 40 },
    xAxis: { type: 'category', name: '序号', data: xs },
    yAxis: { type: 'value', name: d.unit || '测量值', scale: true },
    series: [
      {
        name: '测量值',
        type: 'line',
        data: ys,
        smooth: false,
        symbol: 'circle',
        symbolSize: 7,
        itemStyle: { color: '#0f766e' },
        lineStyle: { width: 2, color: '#0f766e' },
        markLine: {
          symbol: 'none',
          data: markLines,
        },
      },
      {
        name: '失控点',
        type: 'scatter',
        data: ooc.map((p) => [String(p.index), p.value]),
        symbolSize: 12,
        itemStyle: { color: '#dc2626' },
        z: 10,
      },
    ],
  }
})

onMounted(async () => {
  try {
    await loadFilters()
  } catch {
    /* ignore */
  }
  await loadList()
})
</script>

<style scoped>
.spc-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 24px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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
}
.layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 12px;
  min-height: 520px;
}
.chart-list,
.chart-detail {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
}
.chart-list {
  overflow: auto;
  max-height: 720px;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  gap: 8px;
}
.panel-title {
  font-weight: 600;
  font-size: 14px;
}
.panel-hint {
  color: #94a3b8;
  font-size: 12px;
  margin-left: 8px;
}
.chart-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.chart-item:hover {
  border-color: #94a3b8;
}
.chart-item.active {
  border-color: #0f766e;
  background: #f0fdfa;
}
.item-title {
  font-weight: 600;
  font-size: 13px;
}
.item-meta {
  color: #64748b;
  font-size: 12px;
  margin-top: 4px;
}
.item-foot {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 8px;
  font-size: 12px;
  color: #475569;
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}
.kpi {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.kpi span {
  color: #64748b;
  font-size: 11px;
}
.kpi b {
  font-size: 15px;
  color: #0f172a;
}
.kpi b.bad {
  color: #dc2626;
}
.kpi b.ok {
  color: #059669;
}
.spc-chart {
  height: 380px;
  width: 100%;
}
.alert-box {
  margin-top: 10px;
  padding: 8px 12px;
  background: #fef2f2;
  color: #b91c1c;
  border-radius: 8px;
  font-size: 13px;
}
.chart-detail.empty {
  display: flex;
  align-items: center;
  justify-content: center;
}
@media (max-width: 960px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .kpi-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
