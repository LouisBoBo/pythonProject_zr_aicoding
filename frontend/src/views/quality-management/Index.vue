<template>
  <div class="qm-overview">
    <header class="page-header">
      <div>
        <h1 class="page-title">品质管理</h1>
        <p class="page-sub">检验任务、检验记录与品质异常处理入口</p>
      </div>
    </header>
    <div class="link-grid">
      <router-link class="link-card" to="/quality-management/anomalies">
        <strong>品质异常</strong>
        <span>筛选、关闭未处理异常</span>
      </router-link>
      <router-link class="link-card" to="/quality-management/inspection-tasks">
        <strong>检验任务</strong>
        <span>任务列表与状态流转</span>
      </router-link>
      <router-link class="link-card" to="/quality-management/inspection-records">
        <strong>检验记录</strong>
        <span>历史检验结果查询</span>
      </router-link>
      <router-link class="link-card" to="/quality/dashboard">
        <strong>品质看板</strong>
        <span>实时预警与指标</span>
      </router-link>
    </div>
  </div>
</template>

<style scoped>
.qm-overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.page-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.link-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.link-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 18px 20px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.link-card:hover {
  border-color: #93c5fd;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.08);
}

.link-card strong {
  font-size: 15px;
  color: #111827;
}

.link-card span {
  font-size: 13px;
  color: #6b7280;
}

@media (max-width: 640px) {
  .link-grid {
    grid-template-columns: 1fr;
  }
}
</style>
