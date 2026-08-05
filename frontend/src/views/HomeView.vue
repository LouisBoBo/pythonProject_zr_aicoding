<template>
  <div class="home-page">
    <header class="header">
      <h1>ERP 系统首页</h1>
      <div class="user-info" v-if="user">
        <span>{{ user.username }} ({{ user.role }})</span>
        <button class="logout-btn" @click="handleLogout">退出登录</button>
      </div>
    </header>

    <main class="content">
      <div class="placeholder-card">
        <h2>欢迎使用 ERP 系统</h2>
        <p>登录成功，首页功能开发中...</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { clearToken, fetchCurrentUser } from '../api/auth'

const router = useRouter()
const user = ref(null)

onMounted(async () => {
  try {
    user.value = await fetchCurrentUser()
  } catch {
    router.push('/login')
  }
})

function handleLogout() {
  clearToken()
  router.push('/login')
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.header h1 {
  font-size: 20px;
  color: #1a1a2e;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
  color: #555;
}

.logout-btn {
  padding: 6px 16px;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.logout-btn:hover {
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
