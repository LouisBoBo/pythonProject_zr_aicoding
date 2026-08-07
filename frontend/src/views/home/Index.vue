<template>
  <div class="dashboard-home">
    <div class="dashboard-grid">
      <!-- 左列 · 月产量 -->
      <div class="dash-card card-white">
        <div class="card-header">
          <span class="card-title">月产量</span>
        </div>
        <div class="card-body gauge-body">
          <div class="gauge-main-value">{{ formatNumber(monthlyValue) }}</div>
          <v-chart class="gauge-chart" :option="monthlyGaugeOption" autoresize />
          <div class="gauge-footer">
            <span class="gauge-last-value">{{ formatNumber(lastMonthValue) }}</span>
            <span class="gauge-last-label">上一月产量</span>
          </div>
        </div>
      </div>

      <!-- 右列 · 异常分析 -->
      <div class="dash-card card-white">
        <div class="card-header">
          <span class="card-title">异常分析</span>
        </div>
        <div class="card-body donut-body">
          <v-chart class="donut-chart" :option="anomalyDonutOption" autoresize />
          <div class="donut-center">{{ anomalyPercent }}%</div>
          <a class="detail-link" href="javascript:;">详细信息</a>
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
          <div class="daily-percent">{{ dailyPercent }}%</div>
          <a class="detail-link" href="javascript:;">详细信息</a>
        </div>
      </div>

      <!-- 右列 · 产量趋势图（红底分栏） -->
      <div class="dash-card card-split card-red">
        <div class="split-top">
          <div class="card-header">
            <span class="card-title light">产量趋势图</span>
            <span class="card-date light">{{ displayDate }}</span>
          </div>
          <div class="split-chart-area">
            <v-chart class="line-chart" :option="productionTrendOption" autoresize />
          </div>
        </div>
        <div class="split-bottom">
          <span class="split-label">当前生产趋势图</span>
          <span class="split-value">{{ productionTrendValue }}</span>
        </div>
      </div>

      <!-- 左列 · 效率趋势 -->
      <div class="dash-card card-white">
        <div class="card-header">
          <span class="card-title">效率趋势</span>
        </div>
        <div class="card-body">
          <v-chart class="line-chart" :option="efficiencyLineOption" autoresize />
          <div class="efficiency-footer">
            <span class="eff-stat">
              <em>{{ efficiencyCount }}</em>
              <small>数量</small>
            </span>
            <span class="eff-stat">
              <em>{{ efficiencyRate }}%</em>
              <small>比例</small>
            </span>
          </div>
        </div>
      </div>

      <!-- 右列 · 时段产量（橙底分栏） -->
      <div class="dash-card card-split card-orange">
        <div class="split-top">
          <div class="card-header">
            <span class="card-title light">时段产量</span>
            <span class="card-date light">{{ displayDate }}</span>
          </div>
          <div class="split-chart-area">
            <v-chart class="bar-chart" :option="hourlyBarOption" autoresize />
          </div>
        </div>
        <div class="split-bottom">
          <span class="split-label">最近12个小时平均产量</span>
          <span class="split-value">{{ hourlyAvg }}</span>
        </div>
      </div>
    </div>

    <!-- 右侧浮动组件指示 -->
    <div class="float-widget">
      <div class="float-badge">{{ hourlyPercent }}%</div>
      <span class="float-label">桌面组件</span>
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
])

const displayDate = '2022.12.30'
const monthlyValue = 3535
const lastMonthValue = 4590
const dailyCurrent = 1810
const dailyTarget = 2500
const dailyPercent = Math.round((dailyCurrent / dailyTarget) * 100)
const efficiencyCount = 197
const efficiencyRate = 85
const anomalyPercent = 81
const productionTrendValue = '4,316.0'
const hourlyPercent = 79
const hourlyAvg = 20.45

const anomalyItems = [
  { name: '10', value: 10 },
  { name: '20', value: 20 },
  { name: '30', value: 30 },
  { name: '40', value: 40 },
]

const efficiencyTrendData = [62, 68, 72, 78, 75, 82, 80, 85, 83, 88, 86, 85]

const productionTrendData = [3200, 3450, 3680, 3900, 4050, 4180, 4250, 4316]

const hourlyProduction = [18, 22, 15, 12, 10, 12, 8, 5, 6, 10, 18, 25]

const monthlyGaugeOption = computed(() => ({
  series: [
    {
      type: 'gauge',
      startAngle: 180,
      endAngle: 0,
      center: ['50%', '85%'],
      radius: '130%',
      min: 0,
      max: 5000,
      splitNumber: 4,
      axisLine: {
        lineStyle: {
          width: 16,
          color: [
            [0.5, '#e8e8e8'],
            [0.75, '#f5a623'],
            [1, '#e74c3c'],
          ],
        },
      },
      pointer: {
        icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
        length: '52%',
        width: 6,
        offsetCenter: [0, '-8%'],
        itemStyle: { color: '#555' },
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
    right: 8,
    top: 'middle',
    itemWidth: 10,
    itemHeight: 10,
    textStyle: { color: '#666', fontSize: 12 },
    formatter: (name) => name,
  },
  color: ['#48bb78', '#ed8936', '#4299e1', '#cbd5e0'],
  series: [
    {
      type: 'pie',
      radius: ['50%', '72%'],
      center: ['38%', '46%'],
      avoidLabelOverlap: true,
      label: { show: false },
      emphasis: { label: { show: false } },
      data: anomalyItems,
    },
  ],
}))

const productionTrendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 8, right: 8, top: 8, bottom: 8 },
  xAxis: {
    type: 'category',
    show: false,
    data: productionTrendData.map((_, i) => i),
  },
  yAxis: {
    type: 'value',
    show: false,
  },
  series: [
    {
      type: 'line',
      smooth: false,
      data: productionTrendData,
      lineStyle: { color: '#fff', width: 2 },
      itemStyle: { color: '#fff' },
      symbol: 'none',
      areaStyle: { color: 'transparent' },
    },
  ],
}))

const efficiencyLineOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 36, right: 16, top: 16, bottom: 36 },
  xAxis: {
    type: 'category',
    show: false,
    data: efficiencyTrendData.map((_, i) => i),
  },
  yAxis: {
    type: 'value',
    show: false,
    min: 50,
    max: 100,
  },
  series: [
    {
      type: 'line',
      smooth: false,
      data: efficiencyTrendData,
      lineStyle: { color: '#5ec4c4', width: 2 },
      itemStyle: { color: '#5ec4c4', borderColor: '#fff', borderWidth: 2 },
      symbol: 'circle',
      symbolSize: 8,
      areaStyle: { color: 'transparent' },
    },
  ],
}))

const hourlyBarOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 8, right: 8, top: 8, bottom: 8 },
  xAxis: {
    type: 'category',
    show: false,
    data: hourlyProduction.map((_, i) => i),
  },
  yAxis: {
    type: 'value',
    show: false,
  },
  series: [
    {
      type: 'bar',
      data: hourlyProduction,
      barWidth: '60%',
      itemStyle: {
        color: 'rgba(255,255,255,0.85)',
        borderRadius: [2, 2, 0, 0],
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
  position: relative;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: repeat(3, minmax(200px, 1fr));
  gap: 14px;
  min-height: calc(100vh - 180px);
}

.dash-card {
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.card-white {
  background: #fff;
  padding: 14px 16px;
}

.card-split {
  padding: 0;
}

.card-red .split-top {
  background: #c2185b;
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 14px 16px 8px;
  min-height: 0;
}

.card-orange .split-top {
  background: #e65100;
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 14px 16px 8px;
  min-height: 0;
}

.split-bottom {
  background: #fff;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}

.split-label {
  font-size: 12px;
  color: #999;
}

.split-value {
  font-size: 26px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
}

.split-chart-area {
  flex: 1;
  min-height: 80px;
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
  margin-bottom: -8px;
}

.gauge-chart {
  width: 100%;
  height: 110px;
}

.gauge-footer {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-top: -4px;
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
}

.donut-chart {
  height: 100%;
  min-height: 150px;
  width: 100%;
}

.donut-center {
  position: absolute;
  top: 46%;
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
  gap: 10px;
  padding: 4px 0;
}

.daily-values {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.daily-current {
  font-size: 32px;
  font-weight: 700;
  color: #3182ce;
}

.daily-sep {
  font-size: 18px;
  color: #ccc;
  margin: 0 2px;
}

.daily-target {
  font-size: 18px;
  color: #888;
}

.progress-track {
  width: 100%;
  height: 16px;
  background: #edf2f7;
  border-radius: 8px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4299e1 0%, #3182ce 100%);
  border-radius: 8px;
  transition: width 0.6s ease;
}

.daily-percent {
  font-size: 13px;
  color: #718096;
}

.detail-link {
  font-size: 12px;
  color: #409eff;
  text-decoration: none;
  margin-top: 2px;
}

.detail-link:hover {
  text-decoration: underline;
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
  height: 100%;
  min-height: 100px;
}

.card-split {
  display: flex;
  flex-direction: column;
}

.float-widget {
  position: fixed;
  right: 24px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  background: #fff;
  border-radius: 20px;
  padding: 10px 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
  z-index: 10;
}

.float-badge {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.float-label {
  font-size: 10px;
  color: #666;
  writing-mode: vertical-rl;
  letter-spacing: 2px;
}

@media (max-width: 992px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
    min-height: auto;
  }

  .dash-card {
    min-height: 200px;
  }

  .float-widget {
    display: none;
  }
}
</style>
