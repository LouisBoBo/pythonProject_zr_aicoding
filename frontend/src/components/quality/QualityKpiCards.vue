<template>
  <div class="quality-kpi-row">
    <div
      v-for="item in cards"
      :key="item.key"
      class="kpi-card"
      :class="`kpi-${item.key}`"
    >
      <div class="kpi-label">{{ item.label }}</div>
      <div class="kpi-value-row">
        <span class="kpi-value">{{ formatValue(item) }}</span>
        <span v-if="item.unit" class="kpi-unit">{{ item.unit }}</span>
      </div>
      <div v-if="item.change != null" class="kpi-change" :class="changeClass(item)">
        <span class="change-arrow">{{ changeArrow(item) }}</span>
        <span>{{ formatChange(item) }}</span>
        <span class="change-hint">环比</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
})

const cards = computed(() => props.items)

function formatValue(item) {
  if (item.unit === '件') {
    return Math.round(item.value)
  }
  return item.value.toFixed(2)
}

function formatChange(item) {
  if (item.unit === '件') {
    return `${Math.round(item.change)}件`
  }
  return `${item.change?.toFixed(2) ?? 0}%`
}

function changeArrow(item) {
  if (item.change_direction === 'up') return '▲'
  if (item.change_direction === 'down') return '▼'
  return '—'
}

function changeClass(item) {
  if (item.change_direction === 'flat') return 'change-flat'
  const goodUp = item.key === 'yield_rate' || item.key === 'first_pass_yield'
  const goodDown = item.key === 'defect_rate' || item.key === 'scrap_rate' || item.key === 'open_anomalies'
  if (goodUp) {
    return item.change_direction === 'up' ? 'change-good' : 'change-bad'
  }
  if (goodDown) {
    return item.change_direction === 'down' ? 'change-good' : 'change-bad'
  }
  return ''
}
</script>

<style scoped>
.quality-kpi-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.kpi-card {
  padding: 14px 16px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  min-height: 96px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.kpi-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.65);
  letter-spacing: 0.5px;
}

.kpi-value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin: 6px 0;
}

.kpi-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.kpi-unit {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}

.kpi-change {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  color: rgba(255, 255, 255, 0.55);
}

.change-arrow {
  font-size: 10px;
}

.change-hint {
  margin-left: 2px;
  opacity: 0.7;
}

.change-good {
  color: #4ade80;
}

.change-bad {
  color: #f87171;
}

.change-flat {
  color: rgba(255, 255, 255, 0.45);
}

.kpi-yield_rate {
  background: linear-gradient(135deg, rgba(34, 120, 70, 0.35) 0%, rgba(20, 50, 35, 0.6) 100%);
  border-color: rgba(74, 222, 128, 0.2);
}

.kpi-yield_rate .kpi-value {
  color: #4ade80;
}

.kpi-defect_rate {
  background: linear-gradient(135deg, rgba(140, 40, 40, 0.35) 0%, rgba(60, 20, 20, 0.6) 100%);
  border-color: rgba(248, 113, 113, 0.2);
}

.kpi-defect_rate .kpi-value {
  color: #f87171;
}

.kpi-scrap_rate {
  background: linear-gradient(135deg, rgba(160, 90, 20, 0.35) 0%, rgba(70, 45, 10, 0.6) 100%);
  border-color: rgba(251, 191, 36, 0.2);
}

.kpi-scrap_rate .kpi-value {
  color: #fbbf24;
}

.kpi-first_pass_yield {
  background: linear-gradient(135deg, rgba(30, 80, 100, 0.35) 0%, rgba(15, 40, 55, 0.6) 100%);
  border-color: rgba(56, 189, 248, 0.2);
}

.kpi-first_pass_yield .kpi-value {
  color: #38bdf8;
}

.kpi-open_anomalies {
  background: linear-gradient(135deg, rgba(130, 110, 20, 0.35) 0%, rgba(60, 50, 10, 0.6) 100%);
  border-color: rgba(250, 204, 21, 0.2);
}

.kpi-open_anomalies .kpi-value {
  color: #facc15;
}

@media (max-width: 1200px) {
  .quality-kpi-row {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .quality-kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
