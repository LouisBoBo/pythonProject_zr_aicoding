<template>
  <div class="dashboard-home">
    <div class="dashboard-grid">
      <!-- 左列 · 月产量 -->
      <div class="dash-card card-white">
        <div class="card-header">
          <span class="card-title">月产量</span>
        </div>
        <div class="card-body gauge-body">
          <v-chart class="gauge-chart" :option="monthlyGaugeOption" autoresize />
          <div class="gauge-center-value">{{ formatNumber(monthlyValue) }}</div>
        </div>
      </div>

      <!-- 右列 · 异常分析 -->
      <div class="dash-card card-white">
        <div class="card-header">
          <span class="card-title">异常分析</span>
          <span class="card-badge badge-purple">{{ anomalyPercent }}%</span>
        </div>
        <div class="card-body">
          <v-chart class="donut-chart" :option="anomalyDonutOption" autoresize />
        </div>
      </div>

      <!-- 左列 · 日产量 -->
      <div class="dash-card card-white">
        <div class="card-header">
          <span class="card-title">日产量</span>
        </div>
        <div class="card-body daily-body">
          <div class="daily-values">
            <span class="daily-current">{{ dailyCurrent }}</span>
            <span class="daily-sep">/</span>
            <span class="daily-target">{{ dailyTarget }}</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: dailyPercent + '%' }" />
          </div>
          <div class="daily-percent">完成 {{ dailyPercent }}%</div>
        </div>
      </div>

      <!-- 右列 · 产量趋势图（红底） -->
      <div class="dash-card card-red">
        <div class="card-header">
          <span class="card-title light">产量趋势图</span>
          <span class="card-highlight light">{{ productionTrendValue }}</span>
        </div>
        <div class="card-body">
          <v-chart class="line-chart" :option="productionTrendOption" autoresize />
        </div>
      </div>

      <!-- 左列 · 效率趋势 -->
      <div class="dash-card card-white">
        <div class="card-header">
          <span class="card-title">效率趋势</span>
          <div class="efficiency-badges">
            <span class="eff-badge">
              <em>{{ efficiencyCount }}</em> 数量
            </span>
            <span class="eff-badge">
              <em>{{ efficiencyRate }}%</em> 比例
            </span>
          </div>
        </div>
        <div class="card-body">
          <v-chart class="line-chart" :option="efficiencyLineOption" autoresize />
        </div>
      </div>

      <!-- 右列 · 时段产量（橙底） -->
      <div class="dash-card card-orange">
        <div class="card-header">
          <span class="card-title light">时段产量</span>
          <div class="hourly-meta light">
            <span class="card-badge badge-light">{{ hourlyPercent }}%</span>
            <span class="hourly-avg">最近12小时平均产量 {{ hourlyAvg }}</span>
          </div>
        </div>
        <div class="card-body">
          <v-chart class="bar-chart" :option="hourlyBarOption" autoresize />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart, BarChart, GaugeChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkPointComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  BarChart,
  GaugeChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkPointComponent,
])

const monthlyValue = 3535
const dailyCurrent = 1810
const dailyTarget = 2500
const dailyPercent = Math.round((dailyCurrent / dailyTarget) * 100)
const efficiencyCount = 197
const efficiencyRate = 85
const anomalyPercent = 81
const productionTrendValue = '4316.0'
const hourlyPercent = 79
const hourlyAvg = 20.45

const anomalyItems = [
  { name: '设备异常', value: 81 },
  { name: '品质异常', value: 12 },
  { name: '物料异常', value: 5 },
  { name: '其他', value: 2 },
]

const efficiencyTrendData = [72, 78, 75, 82, 80, 85, 83, 88, 86, 85, 87, 85]

const productionTrendData = [3800, 3950, 4020, 4100, 4180, 4250, 4280, 4316]

const hourlyProduction = [
  { hour: '19:00', output: 18 },
  { hour: '20:00', output: 22 },
  { hour: '21:00', output: 15 },
  { hour: '22:00', output: 12 },
  { hour: '23:00', output: 10 },
  { hour: '00:00', output: 12 },
  { hour: '01:00', output: 8 },
  { hour: '02:00', output: 5 },
  { hour: '03:00', output: 6 },
  { hour: '04:00', output: 10 },
  { hour: '05:00', output: 18 },
  { hour: '06:00', output: 25 },
]

const monthlyGaugeOption = computed(() => ({
  series: [
    {
      type: 'gauge',
      startAngle: 180,
      endAngle: 0,
      center: ['50%', '78%'],
      radius: '110%',
      min: 0,
      max: 5000,
      splitNumber: 5,
      axisLine: {
        lineStyle: {
          width: 14,
          color: [
            [0.7, '#5b8def'],
            [0.85, '#48bb78'],
            [1, '#ed8936'],
          ],
        },
      },
      pointer: {
        icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
        length: '55%',
        width: 8,
        offsetCenter: [0, '-10%'],
        itemStyle: { color: '#3d5afe' },
      },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      detail: { show: false },
      data: [{ value: monthlyValue }],
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
  color: ['#667eea', '#48bb78', '#ed8936', '#cbd5e0'],
  series: [
    {
      type: 'pie',
      radius: ['46%', '72%'],
      center: ['36%', '50%'],
      avoidLabelOverlap: true,
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 13, fontWeight: 'bold' },
      },
      data: anomalyItems,
    },
  ],
}))

const productionTrendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 16, top: 16, bottom: 28 },
  xAxis: {
    type: 'category',
    data: productionTrendData.map((_, i) => `${i + 1}月`),
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.35)' } },
    axisLabel: { color: 'rgba(255,255,255,0.75)', fontSize: 11 },
  },
  yAxis: {
    type: 'value',
    axisLine: { show: false },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
    axisLabel: { color: 'rgba(255,255,255,0.75)', fontSize: 11 },
  },
  series: [
    {
      type: 'line',
      smooth: true,
      data: productionTrendData,
      lineStyle: { color: '#fff', width: 2.5 },
      itemStyle: { color: '#fff' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(255,255,255,0.35)' },
            { offset: 1, color: 'rgba(255,255,255,0.02)' },
          ],
        },
      },
    },
  ],
}))

const efficiencyLineOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 16, top: 24, bottom: 28 },
  xAxis: {
    type: 'category',
    data: efficiencyTrendData.map((_, i) => `${i + 1}`),
    axisLine: { lineStyle: { color: '#e8e8e8' } },
    axisLabel: { color: '#999', fontSize: 11 },
  },
  yAxis: {
    type: 'value',
    min: 60,
    max: 100,
    axisLine: { show: false },
    splitLine: { lineStyle: { color: '#f0f0f0' } },
    axisLabel: { color: '#999', fontSize: 11, formatter: '{value}%' },
  },
  series: [
    {
      type: 'line',
      smooth: true,
      data: efficiencyTrendData,
      lineStyle: { color: '#667eea', width: 2.5 },
      itemStyle: { color: '#667eea' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(102, 126, 234, 0.25)' },
            { offset: 1, color: 'rgba(102, 126, 234, 0.02)' },
          ],
        },
      },
      markPoint: {
        symbol: 'circle',
        symbolSize: 8,
        data: [
          {
            coord: [efficiencyTrendData.length - 1, efficiencyRate],
            value: `${efficiencyRate}%`,
            label: {
              show: true,
              formatter: `${efficiencyRate}%`,
              color: '#667eea',
              fontSize: 12,
              fontWeight: 600,
              position: 'top',
            },
            itemStyle: { color: '#667eea' },
          },
        ],
      },
    },
  ],
}))

const hourlyBarOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 36, right: 12, top: 12, bottom: 28 },
  xAxis: {
    type: 'category',
    data: hourlyProduction.map((p) => p.hour),
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.35)' } },
    axisLabel: { color: 'rgba(255,255,255,0.8)', fontSize: 10, rotate: 30 },
  },
  yAxis: {
    type: 'value',
    axisLine: { show: false },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
    axisLabel: { color: 'rgba(255,255,255,0.75)', fontSize: 11 },
  },
  series: [
    {
      type: 'bar',
      data: hourlyProduction.map((p) => p.output),
      barWidth: '55%',
      itemStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(255,255,255,0.95)' },
            { offset: 1, color: 'rgba(255,255,255,0.55)' },
          ],
        },
        borderRadius: [4, 4, 0, 0],
      },
    },
  ],
}))

function formatNumber(num) {
  return num.toLocaleString('zh-CN')
}
</script>

<style scoped>
.dashboard-home {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: repeat(3, minmax(220px, 1fr));
  gap: 16px;
  min-height: calc(100vh - 160px);
}

.dash-card {
  border-radius: 14px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.card-white {
  background: #fff;
}

.card-red {
  background: linear-gradient(135deg, #e53e3e 0%, #fc8181 55%, #feb2b2 100%);
}

.card-orange {
  background: linear-gradient(135deg, #dd6b20 0%, #ed8936 50%, #f6ad55 100%);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.card-title.light {
  color: #fff;
}

.card-highlight {
  font-size: 22px;
  font-weight: 700;
  color: #667eea;
}

.card-highlight.light {
  color: #fff;
}

.card-badge {
  font-size: 16px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 20px;
}

.badge-purple {
  color: #667eea;
  background: rgba(102, 126, 234, 0.12);
}

.badge-light {
  color: #fff;
  background: rgba(255, 255, 255, 0.22);
}

.card-body {
  flex: 1;
  min-height: 0;
  position: relative;
}

.gauge-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
}

.gauge-chart {
  width: 100%;
  height: 140px;
}

.gauge-center-value {
  position: absolute;
  bottom: 28%;
  left: 50%;
  transform: translateX(-50%);
  font-size: 32px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1;
}

.donut-chart {
  height: 100%;
  min-height: 160px;
  width: 100%;
}

.daily-body {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 12px;
  padding: 8px 4px;
}

.daily-values {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.daily-current {
  font-size: 36px;
  font-weight: 700;
  color: #3182ce;
}

.daily-sep {
  font-size: 20px;
  color: #cbd5e0;
}

.daily-target {
  font-size: 20px;
  color: #888;
}

.progress-track {
  height: 14px;
  background: #edf2f7;
  border-radius: 7px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4299e1 0%, #3182ce 100%);
  border-radius: 7px;
  transition: width 0.6s ease;
}

.daily-percent {
  font-size: 13px;
  color: #718096;
  text-align: right;
}

.efficiency-badges {
  display: flex;
  gap: 12px;
}

.eff-badge {
  font-size: 12px;
  color: #888;
}

.eff-badge em {
  font-style: normal;
  font-size: 16px;
  font-weight: 700;
  color: #667eea;
  margin-right: 2px;
}

.line-chart,
.bar-chart {
  width: 100%;
  height: 100%;
  min-height: 150px;
}

.hourly-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hourly-meta.light .hourly-avg {
  color: rgba(255, 255, 255, 0.9);
}

.hourly-avg {
  font-size: 12px;
  color: #888;
}

@media (max-width: 992px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
    min-height: auto;
  }

  .dash-card {
    min-height: 220px;
  }
}
</style>
