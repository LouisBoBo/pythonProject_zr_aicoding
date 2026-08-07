<template>
  <div class="module-placeholder">
    <div class="placeholder-card">
      <el-icon class="placeholder-icon" :size="48"><component :is="icon" /></el-icon>
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
    </div>
  </div>
</template>

<script setup>
import { Document } from '@element-plus/icons-vue'

defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '该模块功能开发中，敬请期待...' },
  icon: { type: Object, default: () => Document },
})
</script>

<style scoped>
.module-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.placeholder-card {
  text-align: center;
  padding: 48px 64px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}

.placeholder-icon {
  color: #667eea;
  margin-bottom: 16px;
}

.placeholder-card h2 {
  font-size: 24px;
  color: #1a1a2e;
  margin-bottom: 12px;
}

.placeholder-card p {
  color: #888;
  font-size: 16px;
}
</style>
