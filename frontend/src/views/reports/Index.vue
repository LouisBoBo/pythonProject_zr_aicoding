<template>
  <div class="reports-hub">
    <el-card shadow="never">
      <template #header>
        <div class="hub-header">
          <el-icon :size="22"><DataLine /></el-icon>
          <span>报表中心</span>
        </div>
      </template>
      <p class="hub-desc">MES 数据统计与可视化报表入口。</p>
      <div class="report-links">
        <router-link to="/reports/wip" class="report-link-card">
          <el-icon :size="28"><Document /></el-icon>
          <span class="link-title">在制品报表</span>
          <span class="link-desc">按工单查看工序与在制数量（wip 口径）</span>
        </router-link>
        <router-link to="/reports/daily-output" class="report-link-card">
          <el-icon :size="28"><DataAnalysis /></el-icon>
          <span class="link-title">日产报表</span>
          <span class="link-desc">按日 / 产线 / 产品查看计划与实际产量</span>
        </router-link>
        <router-link to="/reports/quality-anomalies" class="report-link-card">
          <el-icon :size="28"><Warning /></el-icon>
          <span class="link-title">质量管理</span>
          <span class="link-desc">品质异常明细查询，按状态筛选与分页浏览</span>
        </router-link>
        <router-link to="/reports/equipment" class="report-link-card">
          <el-icon :size="28"><Cpu /></el-icon>
          <span class="link-title">设备管理</span>
          <span class="link-desc">设备档案台账查询，按编号/名称/部门/状态筛选</span>
        </router-link>
        <router-link to="/reports/equipment-repairs" class="report-link-card">
          <el-icon :size="28"><Tools /></el-icon>
          <span class="link-title">设备维修</span>
          <span class="link-desc">维修工单查询、详情查看与 Excel 导出</span>
        </router-link>
        <router-link to="/reports/employee-work-hours" class="report-link-card">
          <el-icon :size="28"><Timer /></el-icon>
          <span class="link-title">员工工时</span>
          <span class="link-desc">按员工/项目/部门统计工时，支持多维度汇总与 Excel 导出</span>
        </router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { Cpu, DataLine, Document, DataAnalysis, Timer, Tools, Warning } from '@element-plus/icons-vue'
</script>

<style scoped>
.reports-hub {
  max-width: 960px;
}

.hub-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.hub-desc {
  color: var(--el-text-color-secondary);
  margin: 0 0 16px;
}

.report-links {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.report-link-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.report-link-card:hover {
  border-color: var(--el-color-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.link-title {
  font-weight: 600;
}

.link-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
