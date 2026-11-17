<template>
  <div class="wb-rich">
    <div v-if="text" class="wb-rich-text">
      <div v-if="streaming" class="ds-stream-plain">{{ text }}</div>
      <div v-else class="ds-md" v-html="renderMd(text)" />
      <span v-if="streaming && text" class="ds-cursor inline" />
    </div>

    <div v-if="tableRows.length && !streaming" class="wb-table-wrap">
      <table class="wb-table">
        <thead>
          <tr>
            <th>{{ headers[0] }}</th>
            <th>{{ headers[1] }}</th>
            <th v-if="hasExtra">备注</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in tableRows" :key="idx">
            <td>{{ row.label }}</td>
            <td class="wb-num">{{ row.value }}</td>
            <td v-if="hasExtra">{{ row.extra }}</td>
          </tr>
          <tr v-if="total != null" class="wb-total">
            <td>合计</td>
            <td class="wb-num">{{ total }} 个</td>
            <td v-if="hasExtra" />
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showLocalChart && !streaming" class="wb-chart-wrap">
      <VChart class="wb-echart" :option="chartOption" autoresize />
    </div>
    <figure v-else-if="chartSrc && !streaming" class="wb-chart-wrap">
      <img :src="chartSrc" alt="数据图表" class="wb-chart" loading="lazy" />
    </figure>

    <p v-if="note && !streaming" class="wb-note">
      <span v-html="formatNote(note)" />
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TitleComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import {
  canRenderTableChart,
  guessTableHeaders,
  normalizeWbTable,
  pickChartTitle,
  sumTableCounts,
  tableToBarChartOption,
} from '../../utils/workbuddyRich'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, TitleComponent])

const props = defineProps({
  text: { type: String, default: '' },
  table: { type: Array, default: () => [] },
  chart: { type: String, default: '' },
  note: { type: String, default: '' },
  streaming: { type: Boolean, default: false },
  renderMd: { type: Function, required: true },
})

const tableRows = computed(() => normalizeWbTable(props.table))
const headers = computed(() => guessTableHeaders(tableRows.value))
const hasExtra = computed(() => tableRows.value.some((r) => r.extra))
const total = computed(() => sumTableCounts(tableRows.value))
const chartSrc = computed(() => props.chart || '')
const showLocalChart = computed(() => canRenderTableChart(tableRows.value))
const chartOption = computed(() =>
  tableToBarChartOption(tableRows.value, { title: pickChartTitle(props.text) }),
)

function formatNote(note) {
  return String(note)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/`([^`]+)`/g, '<code class="wb-inline-code">$1</code>')
    .replace(/(in_progress)/g, '<code class="wb-inline-code">$1</code>')
}
</script>

<style scoped>
.wb-rich {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.wb-rich-text :deep(.ds-md),
.wb-rich-text .ds-stream-plain {
  font-size: 15px;
  line-height: 1.65;
  color: #1f2937;
}

.wb-table-wrap {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}

.wb-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.wb-table th,
.wb-table td {
  padding: 10px 14px;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}

.wb-table th {
  background: #f9fafb;
  color: #374151;
  font-weight: 600;
}

.wb-table td.wb-num {
  font-variant-numeric: tabular-nums;
  color: #111827;
}

.wb-table tr.wb-total td {
  font-weight: 600;
  background: #fafafa;
  border-bottom: none;
}

.wb-chart-wrap {
  margin: 0;
  padding: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
}

.wb-chart {
  display: block;
  max-width: 100%;
  height: auto;
  border-radius: 6px;
}

.wb-echart {
  width: 100%;
  height: 280px;
}

.wb-note {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: #6b7280;
}

.wb-note :deep(.wb-inline-code) {
  background: #f3f4f6;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: #374151;
}

.ds-cursor.inline {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: var(--ds-blue, #4d6bfe);
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: wb-blink 1s step-end infinite;
}

@keyframes wb-blink {
  50% {
    opacity: 0;
  }
}
</style>
