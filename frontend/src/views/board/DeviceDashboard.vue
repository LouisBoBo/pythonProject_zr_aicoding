<template>
  <div class="device-dashboard">
    <!-- ===== 首屏：状态卡片 + OEE ===== -->
    <div class="hero-row">
      <!-- 状态卡片 60% -->
      <div class="status-cards">
        <div
          v-for="card in statusCards"
          :key="card.status"
          class="status-card"
          :style="{ '--card-color': card.color }"
        >
          <div class="card-icon">
            <span :style="{ color: card.color, fontSize: '28px' }">{{ card.icon }}</span>
          </div>
          <div class="card-info">
            <div class="card-label">{{ card.status }}</div>
            <div class="card-count">{{ card.count }}<span class="card-unit"> 台</span></div>
            <div class="card-percent">{{ card.percent }}%</div>
          </div>
          <div class="card-bar" :style="{ background: card.color }"></div>
        </div>
      </div>

      <!-- OEE 仪表盘 40% -->
      <div class="oee-panel">
        <div class="oee-title">综合 OEE</div>
        <div class="oee-gauges">
          <div class="gauge-item" ref="gaugeAvailRef">
            <div class="gauge-chart" ref="chartAvailRef"></div>
            <div class="gauge-label">可用性</div>
          </div>
          <div class="gauge-item" ref="gaugePerfRef">
            <div class="gauge-chart" ref="chartPerfRef"></div>
            <div class="gauge-label">性能</div>
          </div>
          <div class="gauge-item" ref="gaugeQualRef">
            <div class="gauge-chart" ref="chartQualRef"></div>
            <div class="gauge-label">质量</div>
          </div>
        </div>
        <div class="oee-big">
          <span class="oee-value">{{ oeeData.oee.toFixed(1) }}</span>
          <span class="oee-unit">%</span>
        </div>
      </div>
    </div>

    <!-- ===== 次要区：利用率趋势 + 报警统计 ===== -->
    <div class="mid-row">
      <!-- 利用率趋势 -->
      <div class="panel panel-chart">
        <div class="panel-header">
          <span class="panel-title">设备利用率趋势</span>
          <div class="period-btns">
            <button
              v-for="p in periods"
              :key="p.value"
              class="period-btn"
              :class="{ active: period === p.value }"
              @click="switchPeriod(p.value)"
            >{{ p.label }}</button>
          </div>
        </div>
        <div class="chart-wrap" ref="chartUtilRef"></div>
      </div>

      <!-- 报警趋势 + 类型分布 -->
      <div class="panel panel-chart">
        <div class="panel-header">
          <span class="panel-title">设备报警/异常统计</span>
        </div>
        <div class="alarm-charts">
          <div class="chart-wrap-half" ref="chartAlarmBarRef"></div>
          <div class="chart-wrap-half" ref="chartAlarmPieRef"></div>
        </div>
      </div>
    </div>

    <!-- ===== 明细区：设备列表 ===== -->
    <div class="panel bottom-panel">
      <div class="panel-header">
        <span class="panel-title">设备实时状态列表</span>
        <div class="status-filter">
          <button
            v-for="s in statusFilterOptions"
            :key="s"
            class="filter-btn"
            :class="{ active: listStatusFilter === s }"
            @click="listStatusFilter = s; loadDeviceList(1)"
          >{{ s }}</button>
        </div>
      </div>
      <div class="device-table-wrap">
        <table class="device-table">
          <thead>
            <tr>
              <th>设备编号</th>
              <th>设备名称</th>
              <th>当前状态</th>
              <th>运行时长 (h)</th>
              <th>上次报警时间</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in deviceList"
              :key="row.code"
              class="table-row"
            >
              <td class="code-cell">{{ row.code }}</td>
              <td>{{ row.name }}</td>
              <td>
                <span class="status-tag" :style="statusTagStyle(row.status)">{{ row.status }}</span>
              </td>
              <td>{{ row.runtime_hours }}</td>
              <td>{{ row.last_alarm || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="table-footer">
        <span class="table-count">共 {{ deviceListTotal }} 条</span>
        <div class="page-btns">
          <button :disabled="listPage <= 1" @click="loadDeviceList(listPage - 1)">上一页</button>
          <span class="page-num">{{ listPage }} / {{ Math.max(1, Math.ceil(deviceListTotal / listPageSize)) }}</span>
          <button :disabled="listPage >= Math.ceil(deviceListTotal / listPageSize)" @click="loadDeviceList(listPage + 1)">下一页</button>
        </div>
      </div>
    </div>

    <!-- ===== 明细区：产量统计 TOP10 ===== -->
    <div class="panel bottom-panel">
      <div class="panel-header">
        <span class="panel-title">设备产量统计 TOP10</span>
      </div>
      <div class="chart-wrap output-chart" ref="chartOutputRef"></div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import * as echarts from 'echarts'
import {
  fetchDeviceStatusSummary,
  fetchDeviceOEE,
  fetchDeviceDashboardList,
  fetchDeviceUtilization,
  fetchDeviceAlarmsTrend,
  fetchDeviceOutput,
} from '../../api/deviceDashboard'

// ---------- 状态卡片 ----------
const statusCards = ref([])
const statusIconMap = { '运行': '▶', '停机': '■', '待机': '⏸', '维修': '⚙' }

async function loadSummary() {
  try {
    const data = await fetchDeviceStatusSummary()
    statusCards.value = (data.items || []).map(i => ({
      ...i,
      icon: statusIconMap[i.status] || '●',
    }))
  } catch { /* ignore */ }
}

// ---------- OEE ----------
const oeeData = reactive({ availability: 0, performance: 0, quality: 0, oee: 0 })

async function loadOEE() {
  try {
    const d = await fetchDeviceOEE()
    Object.assign(oeeData, d)
  } catch { /* ignore */ }
}

// ---------- OEE Gauges ----------
const chartAvailRef = ref(null)
const chartPerfRef = ref(null)
const chartQualRef = ref(null)
let availChart = null, perfChart = null, qualChart = null

function makeGaugeOption(value, name, color1, color2, color3) {
  return {
    series: [{
      type: 'gauge',
      startAngle: 210,
      endAngle: -30,
      center: ['50%', '60%'],
      radius: '90%',
      min: 0,
      max: 100,
      splitNumber: 5,
      axisLine: {
        show: true,
        lineStyle: {
          width: 12,
          color: [
            [0.3, color1],
            [0.7, color2],
            [1, color3],
          ],
        },
      },
      pointer: {
        icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
        length: '60%',
        width: 6,
        offsetCenter: [0, '-10%'],
        itemStyle: { color: 'auto' },
      },
      axisTick: { distance: -12, length: 6, lineStyle: { width: 1, color: '#555' } },
      splitLine: { distance: -16, length: 14, lineStyle: { width: 2, color: '#555' } },
      axisLabel: { color: '#999', distance: 20, fontSize: 10 },
      detail: {
        valueAnimation: true,
        formatter: '{value}%',
        color: '#fff',
        fontSize: 16,
        offsetCenter: [0, '70%'],
      },
      data: [{ value }],
    }],
  }
}

function renderGauges() {
  if (chartAvailRef.value) {
    availChart = echarts.init(chartAvailRef.value)
    availChart.setOption(makeGaugeOption(oeeData.availability, '可用性', '#52c41a', '#faad14', '#ff4d4f'))
  }
  if (chartPerfRef.value) {
    perfChart = echarts.init(chartPerfRef.value)
    perfChart.setOption(makeGaugeOption(oeeData.performance, '性能', '#1890ff', '#722ed1', '#ff4d4f'))
  }
  if (chartQualRef.value) {
    qualChart = echarts.init(chartQualRef.value)
    qualChart.setOption(makeGaugeOption(oeeData.quality, '质量', '#13c2c2', '#2f54eb', '#ff4d4f'))
  }
}

watch(oeeData, () => nextTick(renderGauges))

// ---------- 利用率 ----------
const period = ref('day')
const periods = [
  { label: '日', value: 'day' },
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
]
const chartUtilRef = ref(null)
let utilChart = null

async function loadUtilization() {
  try {
    const d = await fetchDeviceUtilization(period.value)
    if (utilChart && chartUtilRef.value) {
      utilChart.setOption({
        tooltip: { trigger: 'axis', backgroundColor: 'rgba(20,20,40,0.95)', borderColor: '#333', textStyle: { color: '#ccc' } },
        grid: { left: 50, right: 20, top: 20, bottom: 30 },
        xAxis: {
          type: 'category', data: d.labels,
          axisLine: { lineStyle: { color: '#444' } },
          axisLabel: { color: '#999', fontSize: 10 },
        },
        yAxis: {
          type: 'value', max: 100,
          axisLabel: { color: '#999', formatter: '{value}%' },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        },
        series: [{
          type: 'line',
          data: d.values,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 2, color: '#409eff' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(64,158,255,0.35)' },
              { offset: 1, color: 'rgba(64,158,255,0.02)' },
            ]),
          },
          itemStyle: { color: '#409eff' },
        }],
      }, true)
    }
  } catch { /* ignore */ }
}

function switchPeriod(p) {
  period.value = p
  loadUtilization()
}

// ---------- 报警 ----------
const chartAlarmBarRef = ref(null)
const chartAlarmPieRef = ref(null)
let alarmBarChart = null, alarmPieChart = null

async function loadAlarms() {
  try {
    const d = await fetchDeviceAlarmsTrend()
    if (alarmBarChart && chartAlarmBarRef.value) {
      alarmBarChart.setOption({
        tooltip: { trigger: 'axis', backgroundColor: 'rgba(20,20,40,0.95)', borderColor: '#333', textStyle: { color: '#ccc' } },
        grid: { left: 40, right: 10, top: 10, bottom: 30 },
        xAxis: {
          type: 'category', data: d.labels,
          axisLabel: { color: '#999', fontSize: 9, rotate: 30 },
          axisLine: { lineStyle: { color: '#444' } },
        },
        yAxis: {
          type: 'value',
          axisLabel: { color: '#999' },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        },
        series: [{
          type: 'bar',
          data: d.values,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#ff7a45' },
              { offset: 1, color: '#cf1322' },
            ]),
            borderRadius: [4, 4, 0, 0],
          },
          barWidth: 16,
        }],
      }, true)
    }
    if (alarmPieChart && chartAlarmPieRef.value) {
      alarmPieChart.setOption({
        tooltip: { trigger: 'item', backgroundColor: 'rgba(20,20,40,0.95)', borderColor: '#333', textStyle: { color: '#ccc' } },
        legend: { bottom: 0, textStyle: { color: '#999', fontSize: 10 }, itemWidth: 10, itemHeight: 10 },
        series: [{
          type: 'pie',
          radius: ['45%', '72%'],
          center: ['50%', '42%'],
          avoidLabelOverlap: false,
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 12, fontWeight: 'bold' } },
          data: (d.type_distribution || []).map(t => ({ name: t.name, value: t.value })),
        }],
      }, true)
    }
  } catch { /* ignore */ }
}

// ---------- 设备列表 ----------
const deviceList = ref([])
const deviceListTotal = ref(0)
const listPage = ref(1)
const listPageSize = 20
const listStatusFilter = ref('全部')
const statusFilterOptions = ['全部', '运行', '停机', '待机', '维修']

function statusTagStyle(status) {
  const map = {
    '运行': { background: 'rgba(82,196,26,0.15)', color: '#52c41a', border: '1px solid rgba(82,196,26,0.35)' },
    '停机': { background: 'rgba(255,77,79,0.15)', color: '#ff4d4f', border: '1px solid rgba(255,77,79,0.35)' },
    '待机': { background: 'rgba(250,173,20,0.15)', color: '#faad14', border: '1px solid rgba(250,173,20,0.35)' },
    '维修': { background: 'rgba(250,140,22,0.15)', color: '#fa8c16', border: '1px solid rgba(250,140,22,0.35)' },
  }
  return map[status] || {}
}

async function loadDeviceList(page) {
  listPage.value = page || 1
  try {
    const d = await fetchDeviceDashboardList({
      page: listPage.value,
      pageSize: listPageSize,
      status: listStatusFilter.value === '全部' ? '' : listStatusFilter.value,
    })
    deviceList.value = d.items || []
    deviceListTotal.value = d.total || 0
  } catch { /* ignore */ }
}

// ---------- 产量 ----------
const chartOutputRef = ref(null)
let outputChart = null

async function loadOutput() {
  try {
    const d = await fetchDeviceOutput()
    const items = (d.items || []).slice(0, 10)
    if (outputChart && chartOutputRef.value) {
      outputChart.setOption({
        tooltip: { trigger: 'axis', backgroundColor: 'rgba(20,20,40,0.95)', borderColor: '#333', textStyle: { color: '#ccc' } },
        legend: { data: ['当日产量', '本周产量'], textStyle: { color: '#999' }, top: 0 },
        grid: { left: 130, right: 40, top: 30, bottom: 20 },
        xAxis: {
          type: 'value',
          axisLabel: { color: '#999' },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        },
        yAxis: {
          type: 'category',
          data: items.map(i => i.name).reverse(),
          axisLabel: { color: '#ccc', fontSize: 11 },
          axisLine: { lineStyle: { color: '#444' } },
        },
        series: [
          {
            name: '当日产量', type: 'bar',
            data: items.map(i => i.today_output).reverse(),
            itemStyle: { color: '#409eff', borderRadius: [0, 3, 3, 0] },
            barWidth: 10,
          },
          {
            name: '本周产量', type: 'bar',
            data: items.map(i => i.week_output).reverse(),
            itemStyle: { color: 'rgba(64,158,255,0.3)', borderRadius: [0, 3, 3, 0] },
            barWidth: 10,
          },
        ],
      }, true)
    }
  } catch { /* ignore */ }
}

// ---------- lifecycle ----------
let resizeHandler = null

onMounted(async () => {
  await Promise.all([loadSummary(), loadOEE(), loadAlarms(), loadOutput()])
  await loadDeviceList(1)

  nextTick(() => {
    renderGauges()

    if (chartUtilRef.value) {
      utilChart = echarts.init(chartUtilRef.value)
      loadUtilization()
    }

    if (chartAlarmBarRef.value) {
      alarmBarChart = echarts.init(chartAlarmBarRef.value)
    }
    if (chartAlarmPieRef.value) {
      alarmPieChart = echarts.init(chartAlarmPieRef.value)
    }
    loadAlarms()

    if (chartOutputRef.value) {
      outputChart = echarts.init(chartOutputRef.value)
      loadOutput()
    }
  })

  resizeHandler = () => {
    [availChart, perfChart, qualChart, utilChart, alarmBarChart, alarmPieChart, outputChart].forEach(c => c?.resize?.())
  }
  window.addEventListener('resize', resizeHandler)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeHandler)
  ;[availChart, perfChart, qualChart, utilChart, alarmBarChart, alarmPieChart, outputChart].forEach(c => c?.dispose?.())
})
</script>

<style scoped>
/* ========== 全局深色工业风 ========== */
.device-dashboard {
  background: #1a1a2e;
  min-height: calc(100vh - 140px);
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  color: #e0e0e0;
  font-family: 'Helvetica Neue', 'PingFang SC', sans-serif;
}

/* ========== 面板 ========== */
.panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 16px 20px;
  backdrop-filter: blur(4px);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #ccc;
  letter-spacing: 0.5px;
}

/* ========== 首屏 ========== */
.hero-row {
  display: flex;
  gap: 16px;
  min-height: 280px;
}

/* ---- 状态卡片 ---- */
.status-cards {
  flex: 0 0 60%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.status-card {
  position: relative;
  background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  padding: 18px 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  overflow: hidden;
  transition: border-color 0.3s, box-shadow 0.3s;
}

.status-card:hover {
  border-color: var(--card-color);
  box-shadow: 0 0 18px rgba(0,0,0,0.3), inset 0 0 30px rgba(255,255,255,0.02);
}

.card-bar {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 3px;
  opacity: 0.7;
}

.card-icon {
  width: 48px; height: 48px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 10px;
  background: rgba(255,255,255,0.04);
  flex-shrink: 0;
}

.card-label {
  font-size: 13px; color: #999; margin-bottom: 2px;
}

.card-count {
  font-size: 28px; font-weight: 700; color: #fff; line-height: 1.2;
}

.card-unit { font-size: 14px; font-weight: 400; color: #888; }

.card-percent {
  font-size: 12px; color: #888; margin-top: 2px;
}

/* ---- OEE ---- */
.oee-panel {
  flex: 0 0 40%;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.oee-title {
  font-size: 15px; font-weight: 600; color: #ccc; margin-bottom: 4px;
  letter-spacing: 0.5px;
}

.oee-gauges {
  display: flex;
  gap: 4px;
  flex: 1;
  width: 100%;
}

.gauge-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.gauge-chart {
  width: 100%;
  height: 130px;
}

.gauge-label {
  font-size: 11px; color: #999; margin-top: -12px;
}

.oee-big {
  margin-top: 2px;
  display: flex;
  align-items: baseline;
}

.oee-value {
  font-size: 42px; font-weight: 700;
  background: linear-gradient(135deg, #409eff, #13c2c2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.oee-unit {
  font-size: 16px; color: #888; margin-left: 2px;
}

/* ========== 中期 ========== */
.mid-row {
  display: flex;
  gap: 16px;
  min-height: 320px;
}

.panel-chart {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chart-wrap {
  flex: 1;
  min-height: 260px;
}

.chart-wrap-half {
  flex: 1;
  min-height: 130px;
}

.alarm-charts {
  display: flex;
  flex: 1;
  gap: 8px;
}

.period-btns {
  display: flex;
  gap: 4px;
}

.period-btn {
  padding: 4px 14px;
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 4px;
  background: transparent;
  color: #999;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.25s;
}

.period-btn:hover { border-color: #409eff; color: #409eff; }

.period-btn.active {
  background: rgba(64,158,255,0.2);
  border-color: #409eff;
  color: #409eff;
}

/* ========== 表格 ========== */
.bottom-panel {
  flex: none;
}

.device-table-wrap {
  overflow-x: auto;
}

.device-table {
  width: 100%;
  border-collapse: collapse;
}

.device-table th {
  text-align: left;
  font-size: 12px;
  font-weight: 500;
  color: #888;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.device-table td {
  font-size: 13px;
  color: #ccc;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}

.table-row {
  transition: background 0.2s;
}

.table-row:hover {
  background: rgba(255,255,255,0.04);
}

.code-cell {
  font-family: 'SF Mono', 'Consolas', monospace;
  color: #409eff;
}

.status-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

.status-filter {
  display: flex;
  gap: 4px;
}

.filter-btn {
  padding: 3px 12px;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 12px;
  background: transparent;
  color: #999;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-btn:hover { border-color: #409eff; color: #409eff; }
.filter-btn.active {
  background: rgba(64,158,255,0.2);
  border-color: #409eff;
  color: #409eff;
}

.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
}

.table-count { font-size: 12px; color: #888; }

.page-btns {
  display: flex; align-items: center; gap: 8px;
}

.page-btns button {
  padding: 4px 12px;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 4px;
  background: transparent;
  color: #999;
  font-size: 12px;
  cursor: pointer;
}

.page-btns button:hover:not(:disabled) { border-color: #409eff; color: #409eff; }
.page-btns button:disabled { opacity: 0.35; cursor: default; }

.page-num { font-size: 12px; color: #999; }

/* ========== 产量图 ========== */
.output-chart {
  min-height: 340px;
}
</style>
