<template>
  <div class="production-overview">
    <header class="overview-hero">
      <div class="hero-main">
        <div class="hero-eyebrow">生产管理 · PRODUCTION CONTROL</div>
        <h2 class="hero-title">生产概览</h2>
        <p class="hero-desc">聚焦产出完成、产线负荷、工单结构与在制品分布，一眼掌握生产运行状态</p>
      </div>

      <div class="hero-side">
        <span class="hero-updated">数据更新于 {{ data.updated_at || '--' }}</span>
        <el-button
          class="hero-refresh"
          :icon="Refresh"
          circle
          :loading="loading"
          @click="loadData"
        />
      </div>

      <div class="hero-filters">
        <div class="period-tabs" aria-label="时间范围">
          <button
            v-for="item in periodOptions"
            :key="item.value"
            type="button"
            class="period-chip"
            :class="{ active: filters.period === item.value }"
            @click="setPeriod(item.value)"
          >
            {{ item.label }}
          </button>
        </div>

        <div class="line-filter">
          <span class="filter-label">产线</span>
          <el-select
            v-model="filters.line"
            class="hero-line-select"
            placeholder="请选择产线"
            @change="onFilterChange"
          >
            <el-option v-for="line in lineOptions" :key="line" :label="line" :value="line" />
          </el-select>
        </div>

        <span class="filter-hint">筛选变更后，各图表与指标自动刷新</span>
      </div>
    </header>

    <div v-if="loadError" class="notice">
      <el-alert
        :title="`数据接口暂不可用，已切换至演示数据（${loadError}）`"
        type="warning"
        show-icon
        :closable="false"
      />
    </div>

    <div v-loading="loading" class="overview-body">
      <section class="metric-band">
        <article
          v-for="metric in metrics"
          :key="metric.key"
          class="metric-tile"
          :class="`metric-tile--${metric.tone}`"
        >
          <div class="metric-tile__top">
            <span class="metric-tile__label">{{ metric.label }}</span>
            <span class="metric-tile__trend">{{ metric.trend }}</span>
          </div>
          <div class="metric-tile__value-row">
            <span class="metric-tile__value">{{ metric.value }}</span>
            <span class="metric-tile__unit">{{ metric.unit }}</span>
          </div>
          <div class="metric-tile__bar">
            <span class="metric-tile__bar-fill" :style="{ width: metric.progress + '%' }" />
          </div>
          <div class="metric-tile__sub">{{ metric.sub }}</div>
        </article>
      </section>

      <section class="chart-grid chart-grid--top">
        <ProductionChartPanel
          class="panel-trend"
          title="产量 / 完成趋势"
          :subtitle="trendSubtitle"
          :empty="trendEmpty"
        >
          <v-chart class="chart" :option="trendOption" autoresize />
        </ProductionChartPanel>

        <ProductionChartPanel
          class="panel-achievement"
          title="计划 vs 实际达成"
          :subtitle="achievementSubtitle"
          :empty="achievementEmpty"
        >
          <v-chart class="chart" :option="achievementOption" autoresize />
        </ProductionChartPanel>
      </section>

      <section class="chart-grid chart-grid--middle">
        <ProductionChartPanel
          class="panel-order"
          title="工单状态分布"
          subtitle="待开工 / 进行中 / 完成"
          :empty="orderStatusEmpty"
        >
          <v-chart class="chart" :option="orderStatusOption" autoresize />
        </ProductionChartPanel>

        <ProductionChartPanel
          class="panel-load"
          title="产线负荷 / 产能利用率"
          :subtitle="lineLoadSubtitle"
          :empty="lineLoadEmpty"
        >
          <v-chart class="chart" :option="lineLoadOption" autoresize />
        </ProductionChartPanel>
      </section>

      <section class="chart-grid chart-grid--wip">
        <ProductionChartPanel
          class="panel-wip"
          title="在制品 WIP 概览"
          subtitle="按产线 / 状态分布的横向堆叠分布"
          :empty="wipEmpty"
        >
          <v-chart class="chart" :option="wipOption" autoresize />
        </ProductionChartPanel>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  GraphicComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { Refresh } from '@element-plus/icons-vue'
import ProductionChartPanel from '../../components/production/ProductionChartPanel.vue'
import { fetchProductionOverviewDashboard } from '../../api/productionOverview'
import { buildProductionOverviewMock, PRODUCTION_LINES } from '../../api/productionOverviewMock'

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  GraphicComponent,
])

const COLORS = {
  primary: '#2f6bff',
  primaryDeep: '#1d4ed8',
  green: '#10b981',
  amber: '#f59e0b',
  violet: '#7c3aed',
  cyan: '#06b6d4',
  gray: '#94a3b8',
  text: '#64748b',
  axis: '#e8edf5',
  ink: '#0f172a',
}

const loading = ref(true)
const loadError = ref('')
const filters = reactive({ period: 'day', line: '全部' })
const lineOptions = ['全部', ...PRODUCTION_LINES]
const periodOptions = [
  { value: 'day', label: '日' },
  { value: 'week', label: '周' },
  { value: 'month', label: '月' },
]

function emptyData() {
  return {
    period: 'day',
    production_line: '全部',
    updated_at: '',
    lines: PRODUCTION_LINES,
    kpi: {
      completion_rate: 0,
      completion_rate_trend: '',
      wip_total: 0,
      wip_total_trend: '',
      avg_line_load: 0,
      avg_line_load_trend: '',
      plan_achievement_rate: 0,
      plan_achievement_rate_trend: '',
      plan_quantity: 0,
      actual_quantity: 0,
      achievement_diff: 0,
    },
    achievement_comparison: [],
    output_trend: { labels: [], plan: [], actual: [] },
    work_order_status: [],
    line_load: [],
    wip_overview: { statuses: [], rows: [] },
  }
}

const data = reactive(emptyData())

const axisLabel = { color: COLORS.text, fontSize: 11 }
const axisLine = { lineStyle: { color: COLORS.axis } }
const legendStyle = { color: COLORS.text, fontSize: 12 }

const trendSums = computed(() => ({
  plan: data.output_trend.plan.reduce((sum, value) => sum + Number(value || 0), 0),
  actual: data.output_trend.actual.reduce((sum, value) => sum + Number(value || 0), 0),
}))

const lineLoadBounds = computed(() => {
  const rates = data.line_load.map((item) => Number(item.load_rate || 0))
  if (!rates.length) return { max: 0, min: 0 }
  return { max: Math.max(...rates), min: Math.min(...rates) }
})

function shareOfWip(status) {
  const idx = data.wip_overview.statuses.indexOf(status)
  const total = Number(data.kpi.wip_total || 0)
  if (idx < 0 || !total) return 0
  const count = data.wip_overview.rows.reduce(
    (sum, row) => sum + Number(row.values?.[idx] || 0),
    0,
  )
  return Math.round((count / total) * 100)
}

const wipInProcessShare = computed(() => shareOfWip('在制'))

const metrics = computed(() => {
  const kpi = data.kpi
  const { plan, actual } = trendSums.value
  const bounds = lineLoadBounds.value
  return [
    {
      key: 'completion',
      label: '产量完成率',
      value: formatRate(kpi.completion_rate),
      unit: '%',
      tone: 'primary',
      trend: kpi.completion_rate_trend || '—',
      progress: clampRate(kpi.completion_rate),
      sub: `实际 ${formatNumber(actual)} / 计划 ${formatNumber(plan)} 件`,
    },
    {
      key: 'wip',
      label: '在制品 WIP 总量',
      value: formatNumber(kpi.wip_total),
      unit: '件',
      tone: 'amber',
      trend: kpi.wip_total_trend || '—',
      progress: wipInProcessShare.value,
      sub: `在制占比 ${wipInProcessShare.value}% · 待检 ${shareOfWip('待检验')}%`,
    },
    {
      key: 'load',
      label: '平均产线负荷',
      value: formatRate(kpi.avg_line_load),
      unit: '%',
      tone: 'cyan',
      trend: kpi.avg_line_load_trend || '—',
      progress: clampRate(kpi.avg_line_load),
      sub: `最高 ${formatRate(bounds.max)}% · 最低 ${formatRate(bounds.min)}%`,
    },
    {
      key: 'achievement',
      label: '计划达成率',
      value: formatRate(kpi.plan_achievement_rate),
      unit: '%',
      tone: 'violet',
      trend: kpi.plan_achievement_rate_trend || '—',
      progress: clampRate(kpi.plan_achievement_rate),
      sub: `达成缺口 ${formatNumber(kpi.achievement_diff || 0)} 件`,
    },
  ]
})

const trendSubtitle = computed(() =>
  data.production_line === '全部' ? '时间维度下计划与实际产出' : `时间维度下计划与实际产出 · ${data.production_line}`,
)

const achievementSubtitle = computed(() =>
  data.production_line === '全部' ? '柱状对比计划 / 实际，折线标注达成率' : `按产品对比 · ${data.production_line}`,
)

const lineLoadSubtitle = computed(() =>
  data.production_line === '全部' ? '按产线展示负荷与产能利用' : `按设备展示 · ${data.production_line}`,
)

const trendEmpty = computed(() => !data.output_trend.labels?.length)
const achievementEmpty = computed(() => !data.achievement_comparison?.length)
const orderStatusEmpty = computed(() => !data.work_order_status?.length)
const lineLoadEmpty = computed(() => !data.line_load?.length)
const wipEmpty = computed(() => !data.wip_overview?.rows?.length)

const trendOption = computed(() => {
  const trend = data.output_trend
  return {
    color: [COLORS.gray, COLORS.primary],
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value) => `${formatNumber(value)} 件`,
    },
    legend: {
      data: ['计划产量', '实际产量'],
      right: 0,
      top: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: legendStyle,
    },
    grid: { left: 8, right: 18, top: 40, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: trend.labels,
      axisLine: axisLine,
      axisTick: { show: false },
      axisLabel: axisLabel,
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: COLORS.axis } },
      axisLabel: axisLabel,
    },
    series: [
      {
        name: '计划产量',
        type: 'line',
        data: trend.plan,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: COLORS.gray, type: 'dashed', width: 2 },
      },
      {
        name: '实际产量',
        type: 'line',
        data: trend.actual,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: COLORS.primary, width: 3 },
        itemStyle: { color: COLORS.primary },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(47, 107, 255, 0.18)' },
              { offset: 1, color: 'rgba(47, 107, 255, 0)' },
            ],
          },
        },
      },
    ],
  }
})

const achievementOption = computed(() => {
  const rows = data.achievement_comparison
  return {
    color: [COLORS.gray, COLORS.primary, COLORS.violet],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    legend: {
      data: ['计划数量', '实际数量', '达成率'],
      right: 0,
      top: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: legendStyle,
    },
    grid: { left: 8, right: 8, top: 42, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category',
      data: rows.map((item) => item.name),
      axisLine: axisLine,
      axisTick: { show: false },
      axisLabel: axisLabel,
    },
    yAxis: [
      {
        type: 'value',
        name: '件',
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: COLORS.axis } },
        axisLabel: axisLabel,
      },
      {
        type: 'value',
        name: '%',
        min: 0,
        max: 100,
        position: 'right',
        splitLine: { show: false },
        axisLabel: { ...axisLabel, formatter: '{value}%' },
      },
    ],
    series: [
      {
        name: '计划数量',
        type: 'bar',
        barWidth: 14,
        data: rows.map((item) => item.plan_quantity),
        itemStyle: { color: COLORS.gray, borderRadius: [4, 4, 0, 0] },
      },
      {
        name: '实际数量',
        type: 'bar',
        barWidth: 14,
        data: rows.map((item) => item.actual_quantity),
        itemStyle: { color: COLORS.primary, borderRadius: [4, 4, 0, 0] },
      },
      {
        name: '达成率',
        type: 'line',
        yAxisIndex: 1,
        data: rows.map((item) => item.achievement_rate),
        smooth: false,
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: { color: COLORS.violet, width: 2.5 },
        itemStyle: { color: COLORS.violet },
        label: {
          show: true,
          position: 'top',
          color: COLORS.violet,
          fontSize: 10,
          formatter: '{c}%',
        },
      },
    ],
  }
})

const orderStatusOption = computed(() => {
  const rows = data.work_order_status
  const total = rows.reduce((sum, item) => sum + Number(item.count || 0), 0)
  const colorMap = { 待开工: COLORS.gray, 进行中: COLORS.primary, 完成: COLORS.green }
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} 单 ({d}%)',
    },
    legend: {
      orient: 'vertical',
      right: 4,
      top: 'middle',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: legendStyle,
    },
    graphic: [
      {
        type: 'text',
        left: '30%',
        top: '41%',
        style: {
          text: String(total),
          fill: COLORS.ink,
          fontSize: 24,
          fontWeight: 700,
          textAlign: 'center',
        },
      },
      {
        type: 'text',
        left: '30%',
        top: '56%',
        style: {
          text: '工单总数',
          fill: COLORS.gray,
          fontSize: 11,
          textAlign: 'center',
        },
      },
    ],
    series: [
      {
        type: 'pie',
        radius: ['50%', '70%'],
        center: ['34%', '50%'],
        avoidLabelOverlap: false,
        label: {
          show: true,
          position: 'outside',
          formatter: '{d}%',
          color: COLORS.text,
          fontSize: 11,
        },
        labelLine: { length: 10, length2: 6 },
        data: rows.map((item) => ({
          name: item.status,
          value: item.count,
          itemStyle: { color: colorMap[item.status] || COLORS.gray },
        })),
      },
    ],
  }
})

const lineLoadOption = computed(() => {
  const rows = data.line_load
  return {
    color: [COLORS.primary, COLORS.green],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (value) => `${value}%`,
    },
    legend: {
      data: ['产线负荷', '产能利用率'],
      right: 0,
      top: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: legendStyle,
    },
    grid: { left: 8, right: 8, top: 42, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category',
      data: rows.map((item) => item.name),
      axisLine: axisLine,
      axisTick: { show: false },
      axisLabel: axisLabel,
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: COLORS.axis } },
      axisLabel: { ...axisLabel, formatter: '{value}%' },
    },
    series: [
      {
        name: '产线负荷',
        type: 'bar',
        barWidth: 14,
        data: rows.map((item) => item.load_rate),
        itemStyle: { color: COLORS.primary, borderRadius: [4, 4, 0, 0] },
        label: {
          show: true,
          position: 'top',
          color: COLORS.primary,
          fontSize: 10,
          formatter: '{c}%',
        },
      },
      {
        name: '产能利用率',
        type: 'bar',
        barWidth: 14,
        data: rows.map((item) => item.capacity_utilization),
        itemStyle: { color: COLORS.green, borderRadius: [4, 4, 0, 0] },
        label: {
          show: true,
          position: 'top',
          color: COLORS.green,
          fontSize: 10,
          formatter: '{c}%',
        },
      },
    ],
  }
})

const wipOption = computed(() => {
  const wip = data.wip_overview
  const statuses = wip.statuses || []
  const rows = wip.rows || []
  const wipColors = [COLORS.gray, COLORS.primary, COLORS.amber, COLORS.green]
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (value) => `${formatNumber(value)} 件`,
    },
    legend: {
      data: statuses,
      top: 0,
      left: 'center',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: legendStyle,
    },
    grid: { left: 8, right: 20, top: 40, bottom: 8, containLabel: true },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: COLORS.axis } },
      axisLabel: axisLabel,
    },
    yAxis: {
      type: 'category',
      data: rows.map((item) => item.name),
      axisLine: axisLine,
      axisTick: { show: false },
      axisLabel: axisLabel,
    },
    series: statuses.map((status, si) => ({
      name: status,
      type: 'bar',
      stack: 'wip',
      barWidth: 16,
      data: rows.map((row) => Number(row.values?.[si] || 0)),
      itemStyle: {
        color: wipColors[si % wipColors.length],
        borderRadius: si === statuses.length - 1 ? [0, 6, 6, 0] : 0,
      },
      label: {
        show: true,
        position: 'inside',
        color: '#fff',
        fontSize: 10,
        formatter: ({ value }) => (value > 0 ? value : ''),
      },
      emphasis: { focus: 'series' },
    })),
  }
})

function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN')
}

function formatRate(value) {
  return Number(value || 0).toFixed(1)
}

function clampRate(value) {
  return Math.max(0, Math.min(100, Number(value || 0)))
}

function applyData(resp) {
  data.period = resp.period || filters.period
  data.production_line = resp.production_line || filters.line
  data.updated_at = resp.updated_at || ''
  data.lines = resp.lines?.length ? resp.lines : PRODUCTION_LINES
  data.kpi = { ...emptyData().kpi, ...(resp.kpi || {}) }
  data.achievement_comparison = resp.achievement_comparison || []
  data.output_trend = resp.output_trend || { labels: [], plan: [], actual: [] }
  data.work_order_status = resp.work_order_status || []
  data.line_load = resp.line_load || []
  data.wip_overview = resp.wip_overview || { statuses: [], rows: [] }
}

function setPeriod(period) {
  if (filters.period === period) return
  filters.period = period
  loadData()
}

function onFilterChange() {
  loadData()
}

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
    const resp = await fetchProductionOverviewDashboard({
      period: filters.period,
      line: filters.line,
    })
    applyData(resp)
  } catch (err) {
    loadError.value = err.message || '接口暂不可用'
    applyData(
      buildProductionOverviewMock({
        period: filters.period,
        line: filters.line,
      }),
    )
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.production-overview {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
  color: #1f2937;
}

.overview-hero {
  position: relative;
  border-radius: 16px;
  padding: 20px 22px 16px;
  background:
    radial-gradient(circle at 85% 12%, rgba(96, 165, 250, 0.35), transparent 32%),
    linear-gradient(120deg, #0f172a 0%, #1e3a8a 55%, #2563eb 100%);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.18);
  color: #fff;
  overflow: hidden;
}

.overview-hero::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.06), transparent 40%);
  pointer-events: none;
}

.hero-main {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.hero-eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.6px;
  color: rgba(255, 255, 255, 0.58);
}

.hero-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.4px;
  color: #fff;
}

.hero-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.72);
}

.hero-side {
  position: absolute;
  right: 22px;
  top: 20px;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 12px;
}

.hero-updated {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.68);
  white-space: nowrap;
}

.hero-refresh {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.35);
  background: rgba(255, 255, 255, 0.12);
}

.hero-refresh:hover {
  background: rgba(255, 255, 255, 0.22);
  border-color: rgba(255, 255, 255, 0.55);
}

.hero-filters {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.16);
}

.period-tabs {
  display: flex;
  align-items: center;
  gap: 8px;
}

.period-chip {
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 6px 16px;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.72);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.period-chip:hover {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}

.period-chip.active {
  background: #fff;
  color: #1e3a8a;
  font-weight: 600;
}

.line-filter {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.72);
}

.hero-line-select {
  width: 168px;
}

.hero-line-select :deep(.el-select__wrapper) {
  background: rgba(255, 255, 255, 0.12);
  box-shadow: none;
  border-radius: 8px;
}

.hero-line-select :deep(.el-select__selected-item),
.hero-line-select :deep(.el-select__placeholder) {
  color: rgba(255, 255, 255, 0.85);
}

.hero-line-select :deep(.el-select__caret) {
  color: rgba(255, 255, 255, 0.75);
}

.filter-hint {
  margin-left: auto;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.notice {
  flex-shrink: 0;
}

.overview-body {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 320px;
}

.metric-band {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.metric-tile {
  position: relative;
  min-width: 0;
  border-radius: 14px;
  padding: 16px 18px 14px;
  color: #fff;
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.14);
  overflow: hidden;
}

.metric-tile::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 88% 10%, rgba(255, 255, 255, 0.28), transparent 38%);
  pointer-events: none;
}

.metric-tile--primary {
  background: linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%);
}

.metric-tile--amber {
  background: linear-gradient(135deg, #b45309 0%, #f59e0b 100%);
}

.metric-tile--cyan {
  background: linear-gradient(135deg, #0e7490 0%, #06b6d4 100%);
}

.metric-tile--violet {
  background: linear-gradient(135deg, #5b21b6 0%, #8b5cf6 100%);
}

.metric-tile__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.metric-tile__label {
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.88);
}

.metric-tile__trend {
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.metric-tile__value-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.metric-tile__value {
  font-size: 30px;
  line-height: 1;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.metric-tile__unit {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.72);
}

.metric-tile__bar {
  height: 6px;
  margin-top: 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.22);
  overflow: hidden;
}

.metric-tile__bar-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  transition: width 0.6s ease;
}

.metric-tile__sub {
  margin-top: 10px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.78);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chart-grid {
  display: grid;
  gap: 14px;
}

.chart-grid--top {
  grid-template-columns: 7fr 5fr;
}

.chart-grid--middle {
  grid-template-columns: 5fr 7fr;
}

.chart-grid--wip {
  grid-template-columns: 1fr;
}

.chart {
  width: 100%;
  height: 100%;
  min-width: 0;
}

.panel-trend :deep(.chart-panel__body),
.panel-achievement :deep(.chart-panel__body),
.panel-order :deep(.chart-panel__body),
.panel-load :deep(.chart-panel__body) {
  height: 300px;
}

.panel-wip :deep(.chart-panel__body) {
  height: 268px;
}

@media (max-width: 1180px) {
  .metric-band {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .chart-grid--top,
  .chart-grid--middle {
    grid-template-columns: 1fr;
  }

  .hero-side {
    position: static;
    justify-content: flex-end;
  }
}

@media (max-width: 720px) {
  .metric-band {
    grid-template-columns: 1fr;
  }

  .filter-hint {
    margin-left: 0;
    width: 100%;
  }

  .hero-filters {
    gap: 12px;
  }
}
</style>
