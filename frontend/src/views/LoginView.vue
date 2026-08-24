<template>
  <div class="login-page">
    <!-- 左侧品牌区 ~60% -->
    <div class="login-left">
      <div class="left-header">
        <div class="header-logos">
          <img class="csoft-logo" :src="csoftLogoUrl" alt="中软信息" />
          <span class="logo-divider" aria-hidden="true" />
          <img class="zlpcb-logo" :src="zlpcbLogoUrl" alt="ZLPCB" />
        </div>
        <div class="header-right">
          <h2 class="left-company-title">江西中软电子有限公司</h2>
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
      </div>

      <div class="left-main">
        <div class="hero-visual">
          <img
            class="hero-img"
            src="../assets/login/hero-devices.svg"
            alt="制造执行系统"
          />
        </div>
        <div class="hero-content">
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
        <div class="chart-box chart-line-box">
          <v-chart class="chart-line" :option="lineChartOption" autoresize />
        </div>
        <div class="chart-box chart-pie-box">
          <v-chart class="chart-pie" :option="pieChartOption" autoresize />
        </div>
      </div>

      <footer class="left-footer">
        深圳市前海中软信息技术有限公司 Copyright ©2020-2025 CI.MOM V6.0 All Rights Reserved. 企业热线：400-116-6904
      </footer>
    </div>

    <!-- 右侧表单区 ~40% -->
    <div class="login-right">
      <div class="login-card-wrap">
        <div class="login-card">
          <div class="card-brand">
            <h3 class="card-company">江西中软电子有限公司</h3>
            <p class="card-company-sub">江西中软信息技术有限公司</p>
          </div>

          <el-form class="login-form" @submit.prevent="handleLogin">
            <div class="form-item">
              <label class="form-label">
                <el-icon class="field-icon"><User /></el-icon>
                企业编码
              </label>
              <el-select
                v-model="enterpriseCode"
                placeholder="请选择企业编码"
                class="field-control"
              >
                <el-option
                  v-for="code in enterpriseOptions"
                  :key="code"
                  :label="code"
                  :value="code"
                />
              </el-select>
            </div>

            <div class="form-item">
              <label class="form-label">
                <el-icon class="field-icon"><Document /></el-icon>
                账号
              </label>
              <el-input
                v-model="username"
                placeholder="请输入账号"
                autocomplete="username"
                class="field-control"
              />
            </div>

            <div class="form-item">
              <label class="form-label">
                <el-icon class="field-icon"><Lock /></el-icon>
                密码
              </label>
              <el-input
                v-model="password"
                type="password"
                placeholder="请输入密码"
                autocomplete="current-password"
                show-password
                class="field-control"
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
import csoftLogoUrl from '../assets/login/csoft-logo.svg'
import zlpcbLogoUrl from '../assets/login/zlpcb-logo.svg'

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

const enterpriseOptions = ['江西中软电子有限公司']
const enterpriseCode = ref('江西中软电子有限公司')
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
  grid: { top: 20, right: 16, bottom: 28, left: 40 },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
    axisLabel: { color: 'rgba(255,255,255,0.55)', fontSize: 10 },
    axisTick: { show: false },
  },
  yAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    axisLabel: { color: 'rgba(255,255,255,0.45)', fontSize: 10 },
    axisLine: { show: false },
  },
  series: [
    {
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      data: [120, 182, 191, 234, 290, 330, 310],
      lineStyle: { color: '#52c41a', width: 2 },
      itemStyle: { color: '#52c41a', borderColor: '#fff', borderWidth: 1 },
    },
    {
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      data: [80, 132, 151, 184, 210, 260, 240],
      lineStyle: { color: '#ffd666', width: 2 },
      itemStyle: { color: '#ffd666', borderColor: '#fff', borderWidth: 1 },
    },
    {
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      data: [60, 92, 101, 134, 150, 180, 170],
      lineStyle: { color: '#ff7875', width: 2 },
      itemStyle: { color: '#ff7875', borderColor: '#fff', borderWidth: 1 },
    },
  ],
  tooltip: { trigger: 'axis', backgroundColor: 'rgba(10,26,58,0.9)', borderColor: 'rgba(255,255,255,0.1)' },
}

const pieChartOption = {
  backgroundColor: 'transparent',
  tooltip: { trigger: 'item', backgroundColor: 'rgba(10,26,58,0.9)', borderColor: 'rgba(255,255,255,0.1)' },
  legend: {
    orient: 'vertical',
    right: 0,
    top: 'middle',
    textStyle: { color: 'rgba(255,255,255,0.6)', fontSize: 10 },
    itemWidth: 8,
    itemHeight: 8,
    itemGap: 8,
  },
  series: [
    {
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['36%', '50%'],
      label: { show: false },
      emphasis: { scale: false },
      data: [
        { value: 335, name: '生产', itemStyle: { color: '#52c41a' } },
        { value: 210, name: '品质', itemStyle: { color: '#ffd666' } },
        { value: 154, name: '设备', itemStyle: { color: '#ff7875' } },
        { value: 135, name: '仓储', itemStyle: { color: '#4ecdc4' } },
        { value: 98, name: '其他', itemStyle: { color: '#fa8c16' } },
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
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background:
    radial-gradient(ellipse 80% 60% at 30% 20%, rgba(20, 60, 120, 0.45) 0%, transparent 70%),
    linear-gradient(160deg, #0a1a3a 0%, #123068 38%, #0d2555 68%, #0a1a3a 100%);
}

/* ===== 左侧 60% ===== */
.login-left {
  flex: 0 0 60%;
  display: flex;
  flex-direction: column;
  color: #fff;
  position: relative;
  overflow: hidden;
}

.left-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22px 40px 0;
  flex-shrink: 0;
  gap: 28px;
}

.header-right {
  text-align: right;
  max-width: 58%;
  margin-left: auto;
  /* 标题+标签行整体右移，logo 区与下方展示区位置不变 */
  margin-right: -56px;
  padding-left: 24px;
}

.left-company-title {
  font-size: 17px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
  margin: 0 0 7px;
  letter-spacing: 0.8px;
  white-space: nowrap;
}

.header-logos {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  flex-shrink: 0;
}

.logo-divider {
  width: 1px;
  height: 28px;
  background: rgba(255, 255, 255, 0.18);
  flex-shrink: 0;
}

.csoft-logo {
  height: 38px;
  width: auto;
  display: block;
}

.zlpcb-logo {
  height: 26px;
  width: auto;
  display: block;
}

.left-main {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 8px 36px 0;
  gap: 20px;
  min-height: 0;
}

.hero-visual {
  flex: 0 0 52%;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  min-width: 0;
}

.hero-img {
  width: 100%;
  max-width: 420px;
  min-height: 240px;
  object-fit: contain;
  filter: drop-shadow(0 20px 40px rgba(0, 0, 0, 0.4));
}

.hero-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding-left: 8px;
}

.hero-title {
  margin: 0 0 24px;
  line-height: 1.35;
}

.title-main {
  display: block;
  font-size: 36px;
  font-weight: 700;
  letter-spacing: 3px;
}

.title-sub {
  display: block;
  font-size: 30px;
  font-weight: 600;
  margin-top: 6px;
  letter-spacing: 2px;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.feature-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  color: rgba(255, 255, 255, 0.88);
  padding: 9px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.feature-list li:last-child {
  border-bottom: none;
}

.feature-dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #fff;
}

.charts-row {
  display: flex;
  gap: 16px;
  padding: 12px 36px 8px;
  flex-shrink: 0;
}

.chart-box {
  flex: 1;
  height: 150px;
  border-radius: 4px;
  overflow: hidden;
}

.chart-line-box {
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.chart-pie-box {
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.chart-line,
.chart-pie {
  width: 100%;
  height: 100%;
}

.left-footer {
  flex-shrink: 0;
  padding: 8px 36px 14px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.38);
  line-height: 1.6;
  text-align: center;
}

/* ===== 右侧 40% ===== */
.login-right {
  flex: 0 0 40%;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.top-nav {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
}

.nav-sep {
  color: rgba(255, 255, 255, 0.25);
}

.login-card-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: #ffffff;
  border-radius: 12px;
  padding: 36px 36px 40px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.35), 0 2px 8px rgba(0, 0, 0, 0.2);
}

.card-brand {
  text-align: center;
  margin-bottom: 24px;
}

.card-company {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 5px;
  letter-spacing: 0.3px;
}

.card-company-sub {
  font-size: 12px;
  color: #8c8c8c;
  margin: 0;
  font-weight: 400;
}

.login-form {
  display: flex;
  flex-direction: column;
}

.form-item {
  margin-bottom: 18px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #333;
  margin-bottom: 8px;
  font-weight: 500;
}

.field-icon {
  font-size: 15px;
  color: #888;
}

.field-control {
  width: 100%;
}

.field-control :deep(.el-input__wrapper),
.field-control :deep(.el-select__wrapper) {
  border-radius: 6px;
  box-shadow: 0 0 0 1px #d9d9d9 inset;
  background: #fafafa;
  padding: 4px 12px;
  min-height: 40px;
}

.field-control :deep(.el-input__wrapper:hover),
.field-control :deep(.el-select__wrapper:hover) {
  box-shadow: 0 0 0 1px #b3b3b3 inset;
}

.field-control :deep(.el-input__wrapper.is-focus),
.field-control :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px #1677ff inset;
  background: #fff;
}

.field-control :deep(.el-input__inner),
.field-control :deep(.el-select .el-input__inner) {
  color: #333;
}

.field-control :deep(.el-input__inner::placeholder),
.field-control :deep(.el-select .el-input__inner::placeholder) {
  color: #bbb;
}

.field-control :deep(.el-select .el-select__caret) {
  color: #999;
}

.checkbox-row {
  display: flex;
  align-items: center;
  gap: 18px;
  margin: 4px 0 24px;
  flex-wrap: wrap;
}

.checkbox-row :deep(.el-checkbox__label) {
  font-size: 13px;
  color: #555;
}

.checkbox-row :deep(.el-checkbox__inner) {
  background: #fafafa;
  border-color: #d9d9d9;
}

.error-msg {
  color: #ff4d4f;
  font-size: 13px;
  text-align: center;
  margin: -8px 0 12px;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 6px;
  background: #1677ff;
  border-color: #1677ff;
  color: #fff;
  letter-spacing: 6px;
}

.login-btn:hover,
.login-btn:focus {
  background: #4096ff;
  border-color: #4096ff;
  color: #fff;
}

/* ===== 响应式 ===== */
@media (max-width: 1200px) {
  .top-nav {
    font-size: 11px;
    gap: 4px;
  }

  .title-main {
    font-size: 28px;
  }

  .title-sub {
    font-size: 24px;
  }

  .login-card {
    padding: 28px 24px 32px;
  }
}

@media (max-width: 960px) {
  .login-page {
    flex-direction: column;
    overflow-y: auto;
  }

  .login-left,
  .login-right {
    flex: none;
    width: 100%;
  }

  .login-left {
    min-height: auto;
  }

  .login-right {
    min-height: auto;
  }

  .left-main {
    flex-direction: column;
    text-align: center;
    padding-bottom: 16px;
  }

  .hero-visual {
    flex: none;
    justify-content: center;
  }

  .hero-content {
    align-items: center;
    padding-left: 0;
  }

  .feature-list li {
    justify-content: center;
  }

  .header-right {
    max-width: 100%;
    text-align: center;
    margin-top: 12px;
    margin-right: 0;
    padding-left: 0;
  }

  .left-header {
    flex-direction: column;
    align-items: center;
  }

  .top-nav {
    justify-content: center;
  }

  .charts-row {
    display: none;
  }

  .login-card-wrap {
    padding: 24px 16px 32px;
  }

  .login-card {
    padding: 24px 20px 28px;
  }
}

@media (max-width: 480px) {
  .login-card-wrap {
    padding: 16px 12px 24px;
  }

  .login-card {
    padding: 20px 16px 24px;
    border-radius: 10px;
  }

  .card-company {
    font-size: 18px;
  }

  .checkbox-row {
    gap: 12px;
  }
}
</style>
