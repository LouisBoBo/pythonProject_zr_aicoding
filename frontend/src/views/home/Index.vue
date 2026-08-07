<template>
  <div v-loading="loading" class="dashboard-home">
    <div class="dashboard-top">
      <!-- 月产量 -->
      <div class="dash-card card-white">
        <div class="card-header">
          <span class="card-title">月产量</span>
        </div>
        <div class="card-body gauge-body">
          <div class="gauge-main-value">{{ formatNumber(data.monthly_output) }}</div>
          <v-chart class="gauge-chart" :option="monthlyGaugeOption" autoresize />
          <div class="gauge-footer">
            <span class="gauge-last-value">{{ formatNumber(data.last_month_output) }}</span>
            <span class="gauge-last-label">上一月产量</span>
          </div>
        </div>
      </div>

      <!-- 日产量 · 蓝底 -->
      <div class="dash-card card-blue">
        <div class="card-header">
          <span class="card-title light">日产量</span>
        </div>
        <div class="card-body daily-body">
          <div class="daily-values">
            <span class="daily-current">{{ data.daily_current }}</span>
            <span class="daily-sep">/</span>
            <span class="daily-target">{{ data.daily_target }}</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: dailyPercent + '%' }" />
          </div>
          <div class="daily-percent">{{ dailyPercent }}%</div>
          <a class="detail-link light" href="javascript:;">详细信息</a>
        </div>
      </div>

      <!-- 效率趋势 -->
      <div class="dash-card card-white">
        <div class="card-header">
          <span class="card-title">效率趋势</span>
        </div>
        <div class="card-body efficiency-body">
          <v-chart class="line-chart" :option="efficiencyLineOption" autoresize />
          <div class="efficiency-footer">
            <span class="eff-stat">
              <em>{{ data.efficiency_count }}</em>
              <small>数量</small>
            </span>
            <span class="eff-stat">
              <em>{{ data.efficiency_rate }}%</em>
              <small>比例</small>
            </span>
          </div>
        </div>
      </div>

      <!-- 异常分析 -->
      <div class="dash-card card-white">
        <div class="card-header">
          <span class="card-title">异常分析</span>
        </div>
        <div class="card-body donut-body">
          <v-chart class="donut-chart" :option="anomalyDonutOption" autoresize />
          <div class="donut-center">{{ data.anomaly_percent }}%</div>
          <a class="detail-link" href="javascript:;">详细信息</a>
        </div>
      </div>
    </div>

    <div class="dashboard-bottom">
      <!-- 小时产量 · 绿底大卡 -->
      <div class="dash-card card-hourly">
        <div class="hourly-header">
          <div class="hourly-icon-wrap">
            <el-icon class="hourly-icon"><Lightning /></el-icon>
          </div>
          <span class="hourly-date">{{ data.display_date }}</span>
        </div>
        <div class="hourly-title">小时产量</div>
        <div class="hourly-chart-wrap">
          <v-chart class="hourly-line-chart" :option="hourlyOutputOption" autoresize />
        </div>
        <div class="hourly-overlay">
          <div class="overlay-item">
            <span class="overlay-label">当日生产时间</span>
            <span class="overlay-value">{{ data.hourly_stats.production_time }}</span>
          </div>
          <div class="overlay-item">
            <span class="overlay-label">当日产量</span>
            <span class="overlay-value">{{ data.hourly_stats.daily_output }}</span>
          </div>
          <div class="overlay-item">
            <span class="overlay-label">日平均产量</span>
            <span class="overlay-value">{{ data.hourly_stats.daily_avg }}</span>
          </div>
        </div>
      </div>

      <!-- 产量趋势图 · 红底 -->
      <div class="dash-card card-split card-red">
        <div class="split-top">
          <div class="card-header">
            <span class="card-title light">产量趋势图</span>
            <span class="card-date light">{{ data.display_date }}</span>
          </div>
          <div class="split-chart-area">
            <v-chart class="line-chart" :option="productionTrendOption" autoresize />
          </div>
        </div>
        <div class="split-bottom">
          <span class="split-label">当前生产趋势图</span>
          <span class="split-value">{{ formatTrendValue(data.production_trend_value) }}</span>
        </div>
      </div>

      <!-- 时段产量 · 橙底 -->
      <div class="dash-card card-split card-orange">
        <div class="split-top">
          <div class="card-header">
            <span class="card-title light">时段产量</span>
            <span class="card-date light">{{ data.display_date }}</span>
          </div>
          <div class="split-chart-area">
            <v-chart class="bar-chart" :option="hourlyBarOption" autoresize />
          </div>
        </div>
        <div class="split-bottom">
          <span class="split-label">最近12小时平均产量</span>
          <span class="split-value">{{ data.hourly_avg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Lightning } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart, BarChart, GaugeChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { fetchDashboard } from '../../api/dashboard'

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  BarChart,
  GaugeChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
])

const loading = ref(true)
const loadError = ref('')

const defaultManufacturing = {
  display_date: '2022.12.30',
  monthly_output: 3535,
  last_month_output: 4590,
  daily_current: 1810,
  daily_target: 2500,
  efficiency_count: 197,
  efficiency_rate: 85,
  efficiency_trend: [420, 480, 520, 610, 580, 640, 720, 680, 750, 800, 760, 790],
  anomaly_percent: 81,
  anomaly_segments: [
    { name: '10', value: 10 },
    { name: '20', value: 20 },
    { name: '30', value: 30 },
    { name: '40', value: 40 },
  ],
  production_trend_value: 4316.0,
  production_trend: [3200, 3450, 3680, 3900, 4050, 4180, 4250, 4316],
  hourly_avg: 20.45,
  hourly_bars: [18, 22, 15, 12, 10, 12, 8, 5, 6, 10, 18, 25],
  hourly_output_trend: [150, 375, 420, 500, 160, 140],
  hourly_stats: {
    production_time: '7:08',
    daily_output: 525,
    daily_avg: 354,
  },
}

const data = reactive({ ...defaultManufacturing })

const dailyPercent = computed(() =>
  Math.round((data.daily_current / data.daily_target) * 100),
)

const monthlyGaugeOption = computed(() => ({
  series: [
    {
      type: 'gauge',
      startAngle: 180,
      endAngle: 0,
      center: ['50%', '88%'],
      radius: '140%',
      min: 0,
      max: 5000,
      splitNumber: 4,
      axisLine: {
        lineStyle: {
          width: 18,
          color: [
            [0.55, '#e0e0e0'],
            [0.78, '#f5a623'],
            [1, '#e74c3c'],
          ],
        },
      },
      pointer: {
        icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
        length: '55%',
        width: 7,
        offsetCenter: [0, '-6%'],
        itemStyle: { color: '#c0392b' },
      },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      detail: { show: false },
      data: [{ value: data.monthly_output }],
    },
  ],
}))

const anomalyDonutOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: {
    orient: 'vertical',
    right: 4,
    top: 'middle',
    itemWidth: 10,
    itemHeight: 10,
    textStyle: { color: '#666', fontSize: 12 },
  },
  color: ['#48bb78', '#ecc94b', '#ed8936', '#4299e1'],
  series: [
    {
      type: 'pie',
      radius: ['48%', '70%'],
      center: ['38%', '44%'],
      avoidLabelOverlap: true,
      label: { show: false },
      emphasis: { label: { show: false } },
      data: data.anomaly_segments,
    },
  ],
}))

const productionTrendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 4, right: 4, top: 4, bottom: 4 },
  xAxis: {
    type: 'category',
    show: false,
    data: data.production_trend.map((_, i) => i),
  },
  yAxis: { type: 'value', show: false },
  series: [
    {
      type: 'line',
      smooth: true,
      data: data.production_trend,
      lineStyle: { color: '#fff', width: 2.5 },
      itemStyle: { color: '#fff' },
      symbol: 'none',
      areaStyle: { color: 'rgba(255,255,255,0.08)' },
    },
  ],
}))

const efficiencyLineOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 12, top: 12, bottom: 40 },
  xAxis: {
    type: 'category',
    show: false,
    data: data.efficiency_trend.map((_, i) => i),
  },
  yAxis: {
    type: 'value',
    show: true,
    min: 0,
    max: 800,
    splitNumber: 4,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
    axisLabel: { color: '#aaa', fontSize: 11 },
  },
  series: [
    {
      type: 'line',
      smooth: false,
      data: data.efficiency_trend,
      lineStyle: { color: '#5ec4c4', width: 2 },
      itemStyle: { color: '#5ec4c4', borderColor: '#fff', borderWidth: 2 },
      symbol: 'circle',
      symbolSize: 7,
      areaStyle: { color: 'transparent' },
    },
  ],
}))

const hourlyBarOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 4, right: 4, top: 4, bottom: 4 },
  xAxis: {
    type: 'category',
    show: false,
    data: data.hourly_bars.map((_, i) => i),
  },
  yAxis: { type: 'value', show: false },
  series: [
    {
      type: 'bar',
      data: data.hourly_bars,
      barWidth: '55%',
      itemStyle: {
        color: 'rgba(255,255,255,0.9)',
        borderRadius: [2, 2, 0, 0],
      },
    },
  ],
}))

const hourlyOutputOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 16, right: 120, top: 24, bottom: 16 },
  xAxis: {
    type: 'category',
    show: false,
    boundaryGap: false,
    data: data.hourly_output_trend.map((_, i) => i),
  },
  yAxis: { type: 'value', show: false },
  series: [
    {
      type: 'line',
      smooth: true,
      data: data.hourly_output_trend,
      lineStyle: { color: '#fff', width: 4 },
      itemStyle: { color: '#fff' },
      symbol: 'circle',
      symbolSize: 8,
      label: {
        show: true,
        position: 'top',
        color: '#fff',
        fontSize: 13,
        fontWeight: 600,
        formatter: ({ value }) => value,
      },
      areaStyle: { color: 'transparent' },
    },
  ],
}))

function formatNumber(num) {
  return num.toLocaleString('zh-CN')
}

function formatTrendValue(val) {
  return val.toLocaleString('zh-CN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

function applyManufacturing(m) {
  if (!m) return
  Object.assign(data, {
    display_date: m.display_date,
    monthly_output: m.monthly_output,
    last_month_output: m.last_month_output,
    daily_current: m.daily_current,
    daily_target: m.daily_target,
    efficiency_count: m.efficiency_count,
    efficiency_rate: m.efficiency_rate,
    efficiency_trend: [...m.efficiency_trend],
    anomaly_percent: m.anomaly_percent,
    anomaly_segments: m.anomaly_segments.map((s) => ({ ...s })),
    production_trend_value: m.production_trend_value,
    production_trend: [...m.production_trend],
    hourly_avg: m.hourly_avg,
    hourly_bars: [...m.hourly_bars],
    hourly_output_trend: [...m.hourly_output_trend],
    hourly_stats: { ...m.hourly_stats },
  })
}

onMounted(async () => {
  try {
    const resp = await fetchDashboard()
    applyManufacturing(resp.manufacturing)
  } catch (err) {
    loadError.value = err.message || '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.dashboard-home {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dashboard-top {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.dashboard-bottom {
  display: grid;
  grid-template-columns: 2fr 1fr;
  /* 固定行高，避免 ECharts autoresize 与 1fr 互相撑开形成高度死循环 */
  grid-template-rows: 200px 200px;
  gap: 12px;
  height: 412px;
  max-height: 412px;
}

.dash-card {
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.card-white {
  background: #fff;
  padding: 14px 16px;
}

.card-blue {
  background: linear-gradient(135deg, #4facfe 0%, #3182ce 100%);
  padding: 14px 16px;
}

.card-hourly {
  grid-row: 1 / 3;
  grid-column: 1;
  background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
  padding: 14px 18px;
  position: relative;
  height: 100%;
  min-height: 0;
  max-height: 100%;
  overflow: hidden;
}

.card-split {
  grid-column: 2;
  padding: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  max-height: 100%;
  overflow: hidden;
  box-sizing: border-box;
}

.card-red .split-top {
  background: linear-gradient(135deg, #e91e63 0%, #c2185b 100%);
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  padding: 12px 14px 6px;
  min-height: 0;
  overflow: hidden;
}

.card-orange .split-top {
  background: linear-gradient(135deg, #ff9800 0%, #e65100 100%);
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  padding: 12px 14px 6px;
  min-height: 0;
  overflow: hidden;
}

.split-bottom {
  background: #fff;
  padding: 10px 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 0 0 auto;
  min-height: 58px;
  box-sizing: border-box;
}

.split-label {
  display: block;
  width: 100%;
  font-size: 12px;
  line-height: 1.3;
  color: #999;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.split-value {
  display: block;
  width: 100%;
  font-size: 24px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.split-chart-area {
  flex: none;
  height: 96px;
  max-height: 96px;
  overflow: hidden;
  position: relative;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  flex-shrink: 0;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.card-title.light {
  color: #fff;
}

.card-date {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
}

.card-body {
  flex: 1;
  min-height: 0;
  position: relative;
}

.gauge-body {
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.gauge-main-value {
  font-size: 28px;
  font-weight: 700;
  color: #e74c3c;
  line-height: 1;
  margin-bottom: -6px;
}

.gauge-chart {
  width: 100%;
  height: 100px;
}

.gauge-footer {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-top: -2px;
}

.gauge-last-value {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.gauge-last-label {
  font-size: 12px;
  color: #999;
}

.donut-body {
  position: relative;
  height: 140px;
  max-height: 140px;
  overflow: hidden;
}

.donut-chart {
  width: 100%;
  height: 120px;
  max-height: 120px;
}

.donut-center {
  position: absolute;
  top: 44%;
  left: 38%;
  transform: translate(-50%, -50%);
  font-size: 22px;
  font-weight: 700;
  color: #333;
  pointer-events: none;
}

.daily-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 4px 0;
  min-height: 120px;
}

.daily-values {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.daily-current {
  font-size: 32px;
  font-weight: 700;
  color: #fff;
}

.daily-sep {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 2px;
}

.daily-target {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.75);
}

.progress-track {
  width: 100%;
  height: 18px;
  background: rgba(255, 255, 255, 0.25);
  border-radius: 9px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 9px;
  transition: width 0.6s ease;
}

.daily-percent {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
}

.detail-link {
  font-size: 12px;
  color: #409eff;
  text-decoration: none;
  margin-top: 2px;
}

.detail-link.light {
  color: rgba(255, 255, 255, 0.9);
}

.detail-link:hover {
  text-decoration: underline;
}

.efficiency-body {
  height: 140px;
  max-height: 140px;
  overflow: hidden;
  padding-bottom: 36px;
  box-sizing: border-box;
}

.efficiency-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  padding: 0 4px;
}

.eff-stat {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.eff-stat em {
  font-style: normal;
  font-size: 18px;
  font-weight: 700;
  color: #333;
  line-height: 1.2;
}

.eff-stat small {
  font-size: 11px;
  color: #999;
}

.line-chart,
.bar-chart {
  width: 100%;
  /* 固定像素高度，切断 autoresize ↔ 父容器互相撑开 */
  height: 100px;
  max-height: 100px;
  min-height: 0;
}

.efficiency-body > .line-chart {
  height: 100px;
  max-height: 100px;
}

.split-chart-area > .line-chart,
.split-chart-area > .bar-chart {
  height: 96px;
  max-height: 96px;
}

.hourly-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.hourly-icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
}

.hourly-icon {
  color: #fff;
  font-size: 16px;
}

.hourly-date {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
}

.hourly-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 8px;
}

.hourly-chart-wrap {
  flex: none;
  height: 280px;
  max-height: 280px;
  min-height: 0;
  position: relative;
  overflow: hidden;
}

.hourly-line-chart {
  width: 100%;
  height: 280px;
  max-height: 280px;
  min-height: 0;
}

.hourly-overlay {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(80, 80, 80, 0.55);
  border-radius: 6px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 110px;
}

.overlay-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.overlay-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.75);
  white-space: nowrap;
}

.overlay-value {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  line-height: 1.1;
}

@media (max-width: 1200px) {
  .dashboard-top {
    grid-template-columns: repeat(2, 1fr);
  }

  .dashboard-bottom {
    grid-template-columns: 1fr;
    grid-template-rows: none;
    height: auto;
    max-height: none;
  }

  .card-hourly {
    grid-row: auto;
    grid-column: auto;
    height: auto;
    max-height: none;
    min-height: 0;
  }

  .card-split {
    grid-column: auto;
    height: auto;
    max-height: none;
  }

  .hourly-chart-wrap,
  .hourly-line-chart {
    height: 200px;
    max-height: 200px;
  }
}

@media (max-width: 768px) {
  .dashboard-top {
    grid-template-columns: 1fr;
  }

  .hourly-overlay {
    position: static;
    transform: none;
    margin-top: 12px;
    flex-direction: row;
    justify-content: space-around;
  }
}
</style>
