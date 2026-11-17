<template>
  <section class="chart-panel">
    <header class="chart-panel__head">
      <div class="chart-panel__title-wrap">
        <span class="chart-panel__dot" />
        <div class="chart-panel__title-text">
          <h3 class="chart-panel__title">{{ title }}</h3>
          <p v-if="subtitle" class="chart-panel__subtitle">{{ subtitle }}</p>
        </div>
      </div>
      <div v-if="$slots.extra" class="chart-panel__extra">
        <slot name="extra" />
      </div>
    </header>
    <div class="chart-panel__body">
      <slot />
      <div v-if="empty" class="chart-panel__empty">
        <el-empty :image-size="72" description="暂无数据" />
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: '',
  },
  empty: {
    type: Boolean,
    default: false,
  },
})
</script>

<style scoped>
.chart-panel {
  background: #ffffff;
  border: 1px solid #eef1f6;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(31, 41, 55, 0.04);
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.chart-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px 12px;
  border-bottom: 1px solid #f1f4f9;
}

.chart-panel__title-wrap {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}

.chart-panel__dot {
  width: 4px;
  height: 16px;
  border-radius: 999px;
  background: #2f6bff;
  margin-top: 4px;
  flex-shrink: 0;
}

.chart-panel__title-text {
  min-width: 0;
}

.chart-panel__title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
  color: #1f2937;
}

.chart-panel__subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  line-height: 16px;
  color: #9aa3b2;
}

.chart-panel__extra {
  flex-shrink: 0;
}

.chart-panel__body {
  position: relative;
  flex: 1;
  min-height: 240px;
  min-width: 0;
  padding: 8px 10px 10px;
}

.chart-panel__empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.86);
  z-index: 2;
}
</style>
