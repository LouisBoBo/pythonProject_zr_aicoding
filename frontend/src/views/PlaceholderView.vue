<template>
  <div class="placeholder-page">
    <header class="header">
      <button class="back-btn" @click="router.push('/home')">← 返回首页</button>
      <h1>{{ title }}</h1>
    </header>
    <main class="content">
      <div class="placeholder-card">
        <h2>{{ title }}</h2>
        <p>该模块功能开发中，敬请期待...</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const title = computed(() => route.meta.title || '功能模块')
</script>

<style scoped>
.placeholder-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 32px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.header h1 {
  font-size: 20px;
  color: #1a1a2e;
}

.back-btn {
  padding: 6px 14px;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.back-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

.placeholder-card {
  text-align: center;
  padding: 48px 64px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
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
