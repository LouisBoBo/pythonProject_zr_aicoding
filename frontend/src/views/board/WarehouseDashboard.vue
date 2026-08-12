<template>
  <div v-loading="loading" class="warehouse-dashboard">
    <!-- ===== 顶部 KPI 卡片行 ===== -->
    <div class="kpi-row">
      <div
        v-for="card in kpiCards"
        :key="card.key"
        class="kpi-card"
        :style="{ '--kpi-color': card.color }"
      >
        <div class="kpi-icon">
          <el-icon :size="26"><component :is="card.icon" /></el-icon>
        </div>
        <div class="kpi-info">
          <div class="kpi-label">{{ card.label }}</div>
          <div class="kpi-value">
            <span class="kpi-num">{{ card.value }}</span>
            <span class="kpi-unit">{{ card.unit }}</span>
          </div>
          <div class="kpi-sub">{{ card.sub }}</div>
        </div>
        <div class="kpi-bar" :style="{ background: card.color }"></div>
      </div>
    </div>

    <!-- ===== 中间双图表行（入库趋势 + 出库趋势） ===== -->
    <div class="chart-row">
      <div class="panel chart-panel">
        <div class="panel-header">
          <span class="panel-title">📥 入库趋势</span>
          <div class="period-btns">
            <button
              v-for="p in periods"
              :key="p.value"
              class="period-btn"
              :class="{ active: inboundPeriod === p.value }"
              @click="switchInboundPeriod(p.value)"
            >{{ p.label }}</button>
          </div>
        </div>
        <div class="chart-wrap" ref="inboundChartRef"></div>
      </div>
      <div class="panel chart-panel">
        <div class="panel-header">
          <span class="panel-title">📤 出库趋势</span>
          <div class="period-btns">
            <button
              v-for="p in periods"
              :key="p.value"
              class="period-btn"
              :class="{ active: outboundPeriod === p.value }"
              @click="switchOutboundPeriod(p.value)"
            >{{ p.label }}</button>
          </div>
        </div>
        <div class="chart-wrap" ref="outboundChartRef"></div>
      </div>
    </div>

    <!-- ===== 预警信息条 ===== -->
    <div class="alert-bar">
      <div class="alert-scroll" v-if="alerts.length">
        <span class="alert-icon">⚠️</span>
        <span
          v-for="(alert, i) in alerts"
          :key="i"
          class="alert-tag"
          :class="'alert-' + alert.level"
        >
          {{ alert.text }}
          <span v-if="i < alerts.length - 1" class="alert-sep">|</span>
        </span>
      </div>
      <div v-else class="alert-none">✅ 当前无预警信息</div>
    </div>

    <!-- ===== 下方双栏：库位状态分布 + 实时动态 ===== -->
    <div class="mid-row">
      <div class="panel chart-panel">
        <div class="panel-header">
          <span class="panel-title">📍 库位状态分布</span>
        </div>
        <div class="chart-wrap" ref="locationPieRef"></div>
      </div>
      <div class="panel list-panel">
        <div class="panel-header">
          <span class="panel-title">🔄 实时动态</span>
          <span class="panel-badge">最近 10 条</span>
        </div>
        <div class="activity-list">
          <div
            v-for="(item, idx) in activities"
            :key="idx"
            class="activity-item"
          >
            <span class="activity-time">{{ item.time }}</span>
            <span
              class="activity-tag"
              :class="'tag-' + item.type"
            >{{ item.typeLabel }}</span>
            <span class="activity-text">{{ item.text }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 底部物料明细表格 ===== -->
    <div class="panel table-panel">
      <div class="panel-header">
        <span class="panel-title">📋 物料明细列表</span>
        <div class="table-actions">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索物料名称/编码"
            clearable
            size="small"
            style="width: 200px"
            @input="filterMaterials"
          />
          <el-select
            v-model="categoryFilter"
            placeholder="物料分类"
            clearable
            size="small"
            style="width: 130px; margin-left: 8px"
            @change="filterMaterials"
          >
            <el-option
              v-for="c in categories"
              :key="c"
              :label="c"
              :value="c"
            />
          </el-select>
        </div>
      </div>
      <div class="table-wrap">
        <el-table
          :data="filteredMaterials"
          stripe
          border
          style="width: 100%; min-width: 900px"
          :default-sort="{ prop: 'stock_qty', order: 'descending' }"
          @sort-change="handleSortChange"
        >
          <el-table-column prop="material_code" label="物料编码" min-width="130" sortable="custom" />
          <el-table-column prop="material_name" label="物料名称" min-width="140" />
          <el-table-column prop="category" label="分类" width="100" align="center">
            <template #default="{ row }">
              <el-tag size="small" type="info">{{ row.category }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="spec" label="规格" min-width="120" />
          <el-table-column prop="unit" label="单位" width="70" align="center" />
          <el-table-column prop="stock_qty" label="库存数量" min-width="110" align="right" sortable="custom">
            <template #default="{ row }">
              <span :style="{ color: row.stock_qty < row.safety_stock ? '#f56c6c' : '#e0e0e0', fontWeight: row.stock_qty < row.safety_stock ? 600 : 400 }">
                {{ row.stock_qty.toLocaleString() }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="safety_stock" label="安全库存" min-width="100" align="right" />
          <el-table-column prop="location_code" label="库位编号" min-width="110" align="center" />
          <el-table-column prop="last_update" label="最近更新" min-width="130" align="center" />
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag
                :type="row.stock_qty === 0 ? 'danger' : row.stock_qty < row.safety_stock ? 'warning' : 'success'"
                size="small"
              >
                {{ row.stock_qty === 0 ? '缺货' : row.stock_qty < row.safety_stock ? '低库存' : '正常' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="table-footer">
        <span class="table-count">共 {{ filteredMaterials.length }} 条</span>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="filteredMaterials.length"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          small
          background
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import {
  Box,
  Grid,
  Location,
  RefreshRight,
} from '@element-plus/icons-vue'

// ==================== Mock 数据 ====================

const loading = ref(false)

const kpiCards = [
  { key: 'total_stock', label: '总库存量', value: '1,285,630', unit: '件', sub: '较昨日 +2.3%', color: '#409eff', icon: Box },
  { key: 'sku_count', label: 'SKU 数', value: '4,872', unit: '个', sub: '较上月 +56', color: '#67c23a', icon: Grid },
  { key: 'location_usage', label: '库位使用率', value: '78.5', unit: '%', sub: '空闲 21.5%', color: '#e6a23c', icon: Location },
  { key: 'turnover', label: '周转率', value: '5.8', unit: '次/月', sub: '同比 +0.3', color: '#f56c6c', icon: RefreshRight },
]

// 入库趋势 Mock
const periods = [
  { label: '今日', value: 'today' },
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
]

const inboundData = {
  today: {
    labels: ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00'],
    values: [45, 52, 38, 60, 55, 48, 72, 65, 58, 50],
    summary: 543,
  },
  week: {
    labels: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    values: [320, 410, 380, 450, 520, 280, 180],
    summary: 2540,
  },
  month: {
    labels: ['第1周', '第2周', '第3周', '第4周'],
    values: [1820, 2100, 1950, 2340],
    summary: 8210,
  },
}

const outboundData = {
  today: {
    labels: ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00'],
    values: [38, 45, 32, 55, 48, 42, 68, 60, 52, 44],
    summary: 484,
  },
  week: {
    labels: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    values: [290, 380, 350, 420, 480, 250, 160],
    summary: 2330,
  },
  month: {
    labels: ['第1周', '第2周', '第3周', '第4周'],
    values: [1650, 1920, 1780, 2150],
    summary: 7500,
  },
}

// 预警
const alerts = [
  { level: 'danger', text: '物料「PCB-2024-A」库存低于安全库存（当前 120，安全 200）' },
  { level: 'warning', text: '物料「电阻-0805-10K」已滞库 90 天，请及时处理' },
  { level: 'warning', text: '物料「电容-0603-1uF」临近保质期（剩余 15 天）' },
]

// 库位分布
const locationData = [
  { name: '已占用', value: 235, color: '#409eff' },
  { name: '空闲', value: 65, color: '#67c23a' },
  { name: '异常', value: 12, color: '#f56c6c' },
]

// 实时动态
const activities = [
  { time: '17:32:15', type: 'in', typeLabel: '入库', text: '物料「铝基板-2024」入库 200 件 → A-03-12' },
  { time: '17:28:40', type: 'out', typeLabel: '出库', text: '物料「连接器-USB-C」出库 50 件 ← B-02-05' },
  { time: '17:15:22', type: 'in', typeLabel: '入库', text: '物料「散热片-40x40」入库 500 件 → C-01-08' },
  { time: '17:10:08', type: 'out', typeLabel: '出库', text: '物料「PCB-2024-A」出库 30 件 ← A-01-03' },
  { time: '16:52:33', type: 'move', typeLabel: '移库', text: '物料「电阻-0805-10K」A-02-06 → B-05-11' },
  { time: '16:38:19', type: 'in', typeLabel: '入库', text: '物料「电容-0603-1uF」入库 1000 件 → B-03-02' },
  { time: '16:22:45', type: 'out', typeLabel: '出库', text: '物料「连接器-USB-C」出库 80 件 ← C-02-09' },
  { time: '16:05:11', type: 'check', typeLabel: '盘点', text: '库位 A-03-12 盘点完成，账实相符' },
  { time: '15:48:30', type: 'in', typeLabel: '入库', text: '物料「排针-2.54mm」入库 2000 件 → A-04-07' },
  { time: '15:32:07', type: 'out', typeLabel: '出库', text: '物料「铝基板-2024」出库 120 件 ← B-01-10' },
]

// 物料明细 Mock
const materials = [
  { material_code: 'PCB-2024-A', material_name: '铝基板 PCB', category: '电子元件', spec: '100x160mm', unit: '片', stock_qty: 120, safety_stock: 200, location_code: 'A-01-03', last_update: '2025-01-15 17:30' },
  { material_code: 'RES-0805-10K', material_name: '贴片电阻 10KΩ', category: '电子元件', spec: '0805 ±1%', unit: '个', stock_qty: 8500, safety_stock: 2000, location_code: 'A-02-06', last_update: '2025-01-15 16:50' },
  { material_code: 'CAP-0603-1UF', material_name: '贴片电容 1μF', category: '电子元件', spec: '0603 16V', unit: '个', stock_qty: 3200, safety_stock: 3000, location_code: 'B-03-02', last_update: '2025-01-15 16:38' },
  { material_code: 'CONN-USB-C', material_name: 'USB-C 连接器', category: '连接器', spec: '16P SMT', unit: '个', stock_qty: 180, safety_stock: 500, location_code: 'B-02-05', last_update: '2025-01-15 17:28' },
  { material_code: 'HEATSINK-40', material_name: '铝散热片', category: '散热材料', spec: '40x40x10mm', unit: '片', stock_qty: 2100, safety_stock: 800, location_code: 'C-01-08', last_update: '2025-01-15 17:15' },
  { material_code: 'HEADER-254', material_name: '排针 2.54mm', category: '连接器', spec: '1x40P 直插', unit: '个', stock_qty: 5600, safety_stock: 1500, location_code: 'A-04-07', last_update: '2025-01-15 15:48' },
  { material_code: 'IC-STM32F407', material_name: 'STM32F407VET6', category: '芯片', spec: 'LQFP-100', unit: '片', stock_qty: 320, safety_stock: 100, location_code: 'D-01-01', last_update: '2025-01-14 10:20' },
  { material_code: 'LED-5050-W', material_name: '白光 LED 5050', category: '光电器件', spec: '5050 6000K', unit: '个', stock_qty: 0, safety_stock: 500, location_code: 'D-02-03', last_update: '2025-01-13 14:00' },
  { material_code: 'DIODE-1N4148', material_name: '开关二极管 1N4148', category: '电子元件', spec: 'SOD-123', unit: '个', stock_qty: 4200, safety_stock: 2000, location_code: 'A-05-02', last_update: '2025-01-15 09:12' },
  { material_code: 'IND-4R7', material_name: '功率电感 4.7μH', category: '电子元件', spec: '5x5mm SMD', unit: '个', stock_qty: 1800, safety_stock: 1000, location_code: 'B-04-08', last_update: '2025-01-14 16:30' },
  { material_code: 'XTAL-8M', material_name: '晶振 8MHz', category: '电子元件', spec: '3225 SMD', unit: '个', stock_qty: 650, safety_stock: 300, location_code: 'D-01-05', last_update: '2025-01-13 11:00' },
  { material_code: 'FUSE-2A', material_name: '保险丝 2A', category: '保护器件', spec: '1206 SMD', unit: '个', stock_qty: 3100, safety_stock: 1000, location_code: 'C-03-01', last_update: '2025-01-15 08:45' },
  { material_code: 'MOSFET-N', material_name: 'N沟道 MOSFET', category: '芯片', spec: 'SOT-23 30V/3A', unit: '片', stock_qty: 890, safety_stock: 500, location_code: 'D-01-08', last_update: '2025-01-14 13:20' },
  { material_code: 'SOLDER-PB', material_name: '含铅锡膏', category: '焊接材料', spec: 'Sn63Pb37 500g', unit: '瓶', stock_qty: 45, safety_stock: 20, location_code: 'E-01-01', last_update: '2025-01-15 10:00' },
  { material_code: 'FLUX-100', material_name: '助焊剂', category: '焊接材料', spec: '100ml', unit: '瓶', stock_qty: 28, safety_stock: 15, location_code: 'E-01-02', last_update: '2025-01-12 09:30' },
  { material_code: 'WIRE-AWG22', material_name: '电子线 AWG22', category: '线材', spec: '红 100m/卷', unit: '卷', stock_qty: 12, safety_stock: 10, location_code: 'E-02-03', last_update: '2025-01-11 15:00' },
]

const categories = ['电子元件', '连接器', '芯片', '散热材料', '光电器件', '保护器件', '焊接材料', '线材']

// ==================== 图表相关 ====================

const inboundPeriod = ref('today')
const outboundPeriod = ref('today')
const inboundChartRef = ref(null)
const outboundChartRef = ref(null)
const locationPieRef = ref(null)
let inboundChart = null
let outboundChart = null
let locationPieChart = null

// 物料筛选
const searchKeyword = ref('')
const categoryFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const sortInfo = ref({ prop: 'stock_qty', order: 'descending' })

const filteredMaterials = computed(() => {
  let list = [...materials]
  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase()
    list = list.filter(
      (m) =>
        m.material_name.toLowerCase().includes(kw) ||
        m.material_code.toLowerCase().includes(kw),
    )
  }
  if (categoryFilter.value) {
    list = list.filter((m) => m.category === categoryFilter.value)
  }
  if (sortInfo.value.prop && sortInfo.value.order) {
    const key = sortInfo.value.prop
    const dir = sortInfo.value.order === 'ascending' ? 1 : -1
    list.sort((a, b) => {
      const va = typeof a[key] === 'string' ? a[key] : Number(a[key])
      const vb = typeof b[key] === 'string' ? b[key] : Number(b[key])
      if (va < vb) return -1 * dir
      if (va > vb) return 1 * dir
      return 0
    })
  }
  return list
})

function filterMaterials() {
  currentPage.value = 1
}

function handleSortChange({ prop, order }) {
  sortInfo.value = { prop, order }
}

// ==================== ECharts 渲染 ====================

function makeLineOption(data, colorStart, colorEnd) {
  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(10, 26, 58, 0.95)',
      borderColor: 'rgba(64, 224, 208, 0.3)',
      textStyle: { color: '#fff', fontSize: 12 },
    },
    grid: { left: 48, right: 24, top: 24, bottom: 32 },
    xAxis: {
      type: 'category',
      data: data.labels,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
    },
    series: [
      {
        type: 'line',
        data: data.values,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2.5, color: colorStart },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: colorStart },
            { offset: 1, color: colorEnd },
          ]),
        },
        itemStyle: { color: colorStart },
      },
    ],
  }
}

function renderInboundChart() {
  if (!inboundChart || !inboundChartRef.value) return
  const data = inboundData[inboundPeriod.value]
  inboundChart.setOption(
    makeLineOption(
      data,
      'rgba(64, 158, 255, 0.7)',
      'rgba(64, 158, 255, 0.02)',
    ),
    true,
  )
}

function switchInboundPeriod(p) {
  inboundPeriod.value = p
  renderInboundChart()
}

function renderOutboundChart() {
  if (!outboundChart || !outboundChartRef.value) return
  const data = outboundData[outboundPeriod.value]
  outboundChart.setOption(
    makeLineOption(
      data,
      'rgba(103, 194, 58, 0.7)',
      'rgba(103, 194, 58, 0.02)',
    ),
    true,
  )
}

function switchOutboundPeriod(p) {
  outboundPeriod.value = p
  renderOutboundChart()
}

function renderLocationPie() {
  if (!locationPieChart || !locationPieChartRef.value) return
  locationPieChart.setOption({
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(10, 26, 58, 0.95)',
      borderColor: 'rgba(64, 224, 208, 0.3)',
      textStyle: { color: '#fff' },
      formatter: '{b}: {c} 个 ({d}%)',
    },
    legend: {
      bottom: 8,
      textStyle: { color: 'rgba(255,255,255,0.7)', fontSize: 12 },
      itemWidth: 12,
      itemHeight: 12,
    },
    series: [
      {
        type: 'pie',
        radius: ['55%', '78%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        label: {
          show: true,
          position: 'outside',
          color: 'rgba(255,255,255,0.7)',
          formatter: '{b}\n{d}%',
          fontSize: 11,
        },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 'bold' },
        },
        data: locationData.map((d) => ({
          name: d.name,
          value: d.value,
          itemStyle: { color: d.color },
        })),
      },
    ],
  })
}

// ==================== 生命周期 ====================

let resizeHandler = null

onMounted(() => {
  nextTick(() => {
    if (inboundChartRef.value) {
      inboundChart = echarts.init(inboundChartRef.value)
      renderInboundChart()
    }
    if (outboundChartRef.value) {
      outboundChart = echarts.init(outboundChartRef.value)
      renderOutboundChart()
    }
    if (locationPieRef.value) {
      locationPieChart = echarts.init(locationPieRef.value)
      renderLocationPie()
    }
  })

  resizeHandler = () => {
    [inboundChart, outboundChart, locationPieChart].forEach((c) => c?.resize?.())
  }
  window.addEventListener('resize', resizeHandler)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeHandler)
  ;[inboundChart, outboundChart, locationPieChart].forEach((c) => c?.dispose?.())
})
</script>

<style scoped>
/* ========== 全局深色看板风格 ========== */
.warehouse-dashboard {
  background: #0a1a3a;
  min-height: calc(100vh - 140px);
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  color: #e0e0e0;
  font-family: 'Helvetica Neue', 'PingFang SC', sans-serif;
  margin: -16px -20px;
  width: calc(100% + 40px);
  overflow-x: hidden;
}

/* ========== 面板通用 ========== */
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

.panel-badge {
  font-size: 12px;
  color: #888;
  background: rgba(255,255,255,0.06);
  padding: 2px 10px;
  border-radius: 10px;
}

/* ========== KPI 卡片行 ========== */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.kpi-card {
  position: relative;
  background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 18px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  overflow: hidden;
  transition: border-color 0.3s, box-shadow 0.3s;
}

.kpi-card:hover {
  border-color: var(--kpi-color);
  box-shadow: 0 0 18px rgba(0,0,0,0.3), inset 0 0 30px rgba(255,255,255,0.02);
}

.kpi-bar {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 3px;
  opacity: 0.7;
  border-radius: 0 0 10px 10px;
}

.kpi-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: rgba(255,255,255,0.06);
  flex-shrink: 0;
  color: var(--kpi-color);
}

.kpi-info {
  flex: 1;
  min-width: 0;
}

.kpi-label {
  font-size: 13px;
  color: #999;
  margin-bottom: 2px;
}

.kpi-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.kpi-num {
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
}

.kpi-unit {
  font-size: 13px;
  color: #888;
}

.kpi-sub {
  font-size: 12px;
  color: #888;
  margin-top: 2px;
}

/* ========== 图表行 ========== */
.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.chart-panel {
  display: flex;
  flex-direction: column;
  min-height: 300px;
}

.chart-wrap {
  flex: 1;
  min-height: 260px;
}

/* ========== 时段按钮 ========== */
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

/* ========== 预警条 ========== */
.alert-bar {
  background: rgba(245, 108, 108, 0.08);
  border: 1px solid rgba(245, 108, 108, 0.25);
  border-radius: 8px;
  padding: 10px 16px;
  overflow: hidden;
}

.alert-scroll {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 13px;
}

.alert-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.alert-tag.alert-danger {
  color: #f56c6c;
  font-weight: 500;
}

.alert-tag.alert-warning {
  color: #e6a23c;
}

.alert-sep {
  color: rgba(255,255,255,0.2);
  margin: 0 8px;
}

.alert-none {
  color: #67c23a;
  font-size: 13px;
}

/* ========== 中行双栏 ========== */
.mid-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  min-height: 280px;
}

.list-panel {
  display: flex;
  flex-direction: column;
  min-height: 280px;
}

.activity-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 260px;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 10px;
  background: rgba(255,255,255,0.03);
  border-radius: 6px;
  font-size: 13px;
  transition: background 0.2s;
}

.activity-item:hover {
  background: rgba(255,255,255,0.06);
}

.activity-time {
  font-family: 'SF Mono', 'Consolas', monospace;
  color: #888;
  font-size: 12px;
  flex-shrink: 0;
  width: 62px;
}

.activity-tag {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 4px;
  font-weight: 500;
  flex-shrink: 0;
}

.tag-in {
  background: rgba(64, 158, 255, 0.2);
  color: #409eff;
}

.tag-out {
  background: rgba(103, 194, 58, 0.2);
  color: #67c23a;
}

.tag-move {
  background: rgba(230, 162, 60, 0.2);
  color: #e6a23c;
}

.tag-check {
  background: rgba(144, 147, 153, 0.2);
  color: #909399;
}

.activity-text {
  color: rgba(255,255,255,0.78);
  line-height: 1.4;
  min-width: 0;
}

/* ========== 表格面板 ========== */
.table-panel {
  display: flex;
  flex-direction: column;
  flex: none;
}

.table-actions {
  display: flex;
  align-items: center;
}

.table-wrap {
  overflow-x: auto;
  flex: 1;
}

.table-wrap :deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(10, 40, 80, 0.8);
  --el-table-row-hover-bg-color: rgba(64, 224, 208, 0.06);
  --el-table-border-color: rgba(255,255,255,0.08);
  --el-table-text-color: rgba(255, 255, 255, 0.85);
  --el-table-header-text-color: #40e0d0;
  background: transparent !important;
}

.table-wrap :deep(.el-table th.el-table__cell) {
  background: rgba(10, 40, 80, 0.8) !important;
  color: #40e0d0 !important;
  font-weight: 500;
  font-size: 13px;
  border-bottom: 1px solid rgba(64, 224, 208, 0.15) !important;
  padding: 10px 0;
}

.table-wrap :deep(.el-table td.el-table__cell) {
  background: transparent !important;
  color: rgba(255, 255, 255, 0.82) !important;
  font-size: 13px;
  border-bottom: 1px solid rgba(255,255,255,0.04) !important;
  padding: 8px 0;
}

.table-wrap :deep(.el-table__row--striped td.el-table__cell) {
  background: rgba(255, 255, 255, 0.02) !important;
}

.table-wrap :deep(.el-table__body tr:hover > td.el-table__cell) {
  background: rgba(64, 224, 208, 0.06) !important;
}

.table-wrap :deep(.el-input__wrapper) {
  background: rgba(255,255,255,0.08);
  box-shadow: none;
  border: 1px solid rgba(255,255,255,0.12);
}

.table-wrap :deep(.el-input__inner) {
  color: #e0e0e0;
}

.table-wrap :deep(.el-select .el-input__wrapper) {
  background: rgba(255,255,255,0.08);
  box-shadow: none;
  border: 1px solid rgba(255,255,255,0.12);
}

.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
}

.table-count {
  font-size: 12px;
  color: #888;
}

.table-footer :deep(.el-pagination) {
  --el-pagination-bg-color: transparent;
  --el-pagination-text-color: #ccc;
  --el-pagination-button-color: #ccc;
}

.table-footer :deep(.el-pagination button) {
  background: rgba(255,255,255,0.06) !important;
  border-color: rgba(255,255,255,0.12) !important;
  color: #ccc !important;
}

.table-footer :deep(.el-pagination button.is-active) {
  background: rgba(64, 158, 255, 0.25) !important;
}

.table-footer :deep(.el-pagination .el-select .el-input__wrapper) {
  background: rgba(255,255,255,0.06);
  border-color: rgba(255,255,255,0.12);
}
</style>
