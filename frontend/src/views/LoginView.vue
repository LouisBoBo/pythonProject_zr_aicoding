<template>
  <div class="login-page">
    <!-- 左侧品牌区 ~60% -->
    <div class="login-left">
      <div class="left-header">
        <div class="brand-logo">
          <span class="logo-icon">▲</span>
          <div class="logo-text">
            <span class="logo-name">中软信息</span>
            <span class="logo-url">www.cssoft.cn</span>
          </div>
        </div>
        <nav class="top-nav">
          <span>开源定制</span>
          <span class="nav-sep">|</span>
          <span>多层架构</span>
          <span class="nav-sep">|</span>
          <span>原子开发</span>
          <span class="nav-sep">|</span>
          <span>多数据库</span>
          <span class="nav-sep">|</span>
          <span>多样式展现</span>
          <span class="nav-sep">|</span>
          <span>分布式部署</span>
          <span class="nav-sep">|</span>
          <span>行业套件</span>
        </nav>
      </div>

      <div class="left-main">
        <div class="hero-visual">
          <img
            class="hero-img"
            src="https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=600&h=400&fit=crop"
            alt="制造执行系统"
          />
        </div>
        <div class="hero-content">
          <div class="zlpcb-badge">
            <span class="zlpcb-icon">L</span>
            <span class="zlpcb-text">ZLPCB</span>
          </div>
          <h1 class="hero-title">
            <span class="title-main">中软信息</span>
            <span class="title-sub">制造执行系统</span>
          </h1>
          <ul class="feature-list">
            <li v-for="item in features" :key="item">
              <span class="feature-dot" />
              {{ item }}
            </li>
          </ul>
        </div>
      </div>

      <div class="charts-row">
        <div class="chart-box">
          <v-chart class="chart-line" :option="lineChartOption" autoresize />
        </div>
        <div class="chart-box">
          <v-chart class="chart-pie" :option="pieChartOption" autoresize />
        </div>
      </div>

      <footer class="left-footer">
        深圳市前海中软信息技术有限公司 Copyright ©2020-2025 CI.MOM V6.0 All Rights Reserved. 企业热线：400-116-6904
      </footer>
    </div>

    <!-- 右侧表单区 ~40% -->
    <div class="login-right">
      <h2 class="right-company-title">江西中络电子有限公司</h2>

      <div class="login-card">
        <div class="card-brand">
          <div class="card-zlpcb">
            <span class="card-zlpcb-icon">L</span>
            <span class="card-zlpcb-text">ZLPCB</span>
          </div>
          <h3 class="card-company">江西中络电子有限公司</h3>
          <p class="card-company-sub">江西中络电子有限公司</p>
        </div>

        <el-form class="login-form" @submit.prevent="handleLogin">
          <div class="form-field">
            <el-icon class="field-icon"><User /></el-icon>
            <el-select
              v-model="enterpriseCode"
              placeholder="请选择企业编码"
              class="field-select"
            >
              <el-option
                v-for="code in enterpriseOptions"
                :key="code"
                :label="code"
                :value="code"
              />
            </el-select>
          </div>

          <div class="form-field">
            <el-icon class="field-icon"><Document /></el-icon>
            <el-input
              v-model="username"
              placeholder="请输入账号"
              autocomplete="username"
            />
          </div>

          <div class="form-field">
            <el-icon class="field-icon"><Lock /></el-icon>
            <el-input
              v-model="password"
              type="password"
              placeholder="请输入密码"
              autocomplete="current-password"
              show-password
            />
          </div>

          <div class="checkbox-row">
            <el-checkbox v-model="rememberPassword">记住密码</el-checkbox>
            <el-checkbox v-model="rememberAccount">记住账号</el-checkbox>
            <el-checkbox v-model="autoLogin">自动登录</el-checkbox>
          </div>

          <p v-if="error" class="error-msg">{{ error }}</p>

          <el-button
            type="primary"
            class="login-btn"
            :loading="loading"
            native-type="submit"
          >
            登录
          </el-button>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { User, Document, Lock } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { login } from '../api/auth'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const router = useRouter()
const route = useRoute()

const features = [
  '派工单管理',
  '防错防呆',
  '异常预警',
  '全流程追溯',
  '报表看板管理',
]

const enterpriseOptions = ['江西中络电子有限公司']
const enterpriseCode = ref('江西中络电子有限公司')
const username = ref('')
const password = ref('')
const rememberPassword = ref(false)
const rememberAccount = ref(false)
const autoLogin = ref(false)
const error = ref('')
const loading = ref(false)

const STORAGE_KEY = 'erp_login_prefs'

const lineChartOption = {
  backgroundColor: 'transparent',
  grid: { top: 16, right: 12, bottom: 24, left: 36 },
  xAxis: {
    type: 'category',
    data: ['1月', '2月', '3月', '4月', '5月', '6月'],
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } },
    axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10 },
    axisTick: { show: false },
  },
  yAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
    axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 10 },
    axisLine: { show: false },
  },
  series: [
    {
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 5,
      data: [820, 932, 901, 934, 1290, 1330],
      lineStyle: { color: '#4ecdc4', width: 2 },
      itemStyle: { color: '#4ecdc4' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(78, 205, 196, 0.35)' },
            { offset: 1, color: 'rgba(78, 205, 196, 0.02)' },
          ],
        },
      },
    },
  ],
  tooltip: { trigger: 'axis' },
}

const pieChartOption = {
  backgroundColor: 'transparent',
  tooltip: { trigger: 'item' },
  legend: {
    orient: 'vertical',
    right: 4,
    top: 'center',
    textStyle: { color: 'rgba(255,255,255,0.65)', fontSize: 10 },
    itemWidth: 8,
    itemHeight: 8,
  },
  series: [
    {
      type: 'pie',
      radius: ['38%', '62%'],
      center: ['38%', '50%'],
      label: { show: false },
      data: [
        { value: 335, name: '生产', itemStyle: { color: '#4ecdc4' } },
        { value: 210, name: '品质', itemStyle: { color: '#45b7aa' } },
        { value: 154, name: '设备', itemStyle: { color: '#3a9d8f' } },
        { value: 135, name: '仓储', itemStyle: { color: '#2d8578' } },
      ],
    },
  ],
}

function loadPrefs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const prefs = JSON.parse(raw)
    if (prefs.rememberAccount && prefs.username) {
      username.value = prefs.username
      rememberAccount.value = true
    }
    if (prefs.rememberPassword && prefs.password) {
      password.value = prefs.password
      rememberPassword.value = true
    }
    if (prefs.autoLogin) {
      autoLogin.value = true
    }
    if (prefs.enterpriseCode) {
      enterpriseCode.value = prefs.enterpriseCode
    }
  } catch {
    /* ignore */
  }
}

function savePrefs() {
  const prefs = {
    rememberAccount: rememberAccount.value,
    rememberPassword: rememberPassword.value,
    autoLogin: autoLogin.value,
    username: rememberAccount.value ? username.value : '',
    password: rememberPassword.value ? password.value : '',
    enterpriseCode: enterpriseCode.value,
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
}

async function handleLogin() {
  error.value = ''
  if (!username.value.trim()) {
    error.value = '请输入账号'
    return
  }
  if (!password.value) {
    error.value = '请输入密码'
    return
  }

  loading.value = true
  try {
    await login(username.value, password.value, enterpriseCode.value)
    savePrefs()
    const redirect = route.query.redirect || '/home'
    router.push(redirect)
  } catch (err) {
    error.value = err.message || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadPrefs()
})
</script>

<style scoped>
.login-page {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* ===== 左侧 ===== */
.login-left {
  flex: 0 0 60%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(160deg, #0a1a3a 0%, #0d2b5e 55%, #0a2048 100%);
  color: #fff;
  position: relative;
  overflow: hidden;
}

.left-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 32px 0;
  flex-shrink: 0;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  font-size: 22px;
  color: #fff;
  line-height: 1;
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-name {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
}

.logo-url {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.55);
  margin-top: 2px;
}

.top-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
}

.nav-sep {
  color: rgba(255, 255, 255, 0.25);
}

.left-main {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 16px 32px;
  gap: 24px;
  min-height: 0;
}

.hero-visual {
  flex: 0 0 42%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-img {
  width: 100%;
  max-width: 320px;
  border-radius: 8px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
  object-fit: cover;
}

.hero-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.zlpcb-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 16px;
}

.zlpcb-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, #52c41a, #389e0d);
  border-radius: 4px;
  font-weight: 700;
  font-size: 16px;
  color: #fff;
}

.zlpcb-text {
  display: inline-block;
  padding: 4px 10px;
  background: #fa8c16;
  border-radius: 3px;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 1px;
}

.hero-title {
  margin-bottom: 20px;
  line-height: 1.3;
}

.title-main {
  display: block;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 2px;
}

.title-sub {
  display: block;
  font-size: 26px;
  font-weight: 600;
  margin-top: 4px;
  letter-spacing: 1px;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.feature-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.85);
  padding: 7px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.feature-list li:last-child {
  border-bottom: none;
}

.feature-dot {
  flex-shrink: 0;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #52c41a;
}

.charts-row {
  display: flex;
  gap: 12px;
  padding: 0 32px 12px;
  flex-shrink: 0;
}

.chart-box {
  flex: 1;
  height: 120px;
  background: rgba(0, 0, 0, 0.22);
  border-radius: 6px;
  padding: 4px;
  backdrop-filter: blur(4px);
}

.chart-line,
.chart-pie {
  width: 100%;
  height: 100%;
}

.left-footer {
  flex-shrink: 0;
  padding: 10px 32px 14px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  line-height: 1.5;
  text-align: center;
}

/* ===== 右侧 ===== */
.login-right {
  flex: 0 0 40%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  padding: 32px 40px;
}

.right-company-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 28px;
  text-align: center;
}

.login-card {
  width: 100%;
  max-width: 380px;
  background: #fff;
  border-radius: 8px;
  padding: 36px 32px 32px;
  box-shadow:
    inset 0 1px 3px rgba(0, 0, 0, 0.06),
    0 4px 24px rgba(0, 0, 0, 0.08);
}

.card-brand {
  text-align: center;
  margin-bottom: 28px;
}

.card-zlpcb {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
}

.card-zlpcb-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #52c41a, #389e0d);
  border-radius: 4px;
  font-weight: 700;
  font-size: 18px;
  color: #fff;
}

.card-zlpcb-text {
  display: inline-block;
  padding: 5px 12px;
  background: #fa8c16;
  border-radius: 3px;
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 1px;
}

.card-company {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 4px;
}

.card-company-sub {
  font-size: 13px;
  color: #999;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.form-field {
  display: flex;
  align-items: center;
  border-bottom: 1px solid #e8e8e8;
  padding: 4px 0;
  margin-bottom: 4px;
}

.field-icon {
  flex-shrink: 0;
  font-size: 18px;
  color: #bbb;
  margin-right: 10px;
}

.form-field :deep(.el-input),
.form-field :deep(.el-select) {
  flex: 1;
}

.form-field :deep(.el-input__wrapper) {
  box-shadow: none !important;
  background: transparent;
  padding: 8px 0;
}

.form-field :deep(.el-select__wrapper) {
  box-shadow: none !important;
  background: transparent;
  padding: 8px 0;
}

.checkbox-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 16px 0 20px;
  flex-wrap: wrap;
}

.checkbox-row :deep(.el-checkbox__label) {
  font-size: 13px;
  color: #666;
}

.error-msg {
  color: #e53e3e;
  font-size: 13px;
  text-align: center;
  margin-bottom: 12px;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 6px;
  background: #1a5cd4;
  border-color: #1a5cd4;
  letter-spacing: 4px;
}

.login-btn:hover,
.login-btn:focus {
  background: #1449b0;
  border-color: #1449b0;
}

/* ===== 响应式 ===== */
@media (max-width: 1100px) {
  .top-nav {
    display: none;
  }

  .left-main {
    flex-direction: column;
    text-align: center;
  }

  .hero-visual {
    flex: none;
    max-width: 260px;
  }

  .hero-content {
    align-items: center;
  }

  .feature-list li {
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .login-page {
    flex-direction: column;
    overflow-y: auto;
  }

  .login-left {
    flex: none;
    min-height: 50vh;
  }

  .login-right {
    flex: none;
    min-height: 50vh;
  }

  .charts-row {
    display: none;
  }
}
</style>
