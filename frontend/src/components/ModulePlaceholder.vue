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
  min-height: calc(100vh - 140px);
  padding: 24px;
}

.placeholder-card {
  text-align: center;
  padding: 52px 64px;
  max-width: 480px;
  background: #fff;
  border: 1px solid #e8ecf1;
  border-radius: 12px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
}

.placeholder-icon {
  color: #667eea;
  margin-bottom: 16px;
  padding: 14px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.12), rgba(118, 75, 162, 0.08));
}

.placeholder-card h2 {
  font-size: 22px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 10px;
}

.placeholder-card p {
  color: #909399;
  font-size: 14px;
  line-height: 1.6;
}
</style>
