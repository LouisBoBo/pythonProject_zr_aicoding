<template>
  <div class="reports-hub">
    <el-card shadow="never">
      <template #header>
        <div class="hub-header">
          <el-icon :size="22"><DataLine /></el-icon>
          <span>报表中心</span>
        </div>
      </template>
      <p class="hub-desc">
        MES 数据统计与可视化报表入口。{{ pipelineSummary }}
      </p>
      <el-collapse v-model="prefsOpen" class="prefs-collapse">
        <el-collapse-item title="开发流水线与澄清约定" name="prefs">
          <ul class="prefs-list">
            <li v-for="item in pipelinePreferences" :key="item.id">
              <strong>{{ item.title }}：</strong>{{ item.detail }}
            </li>
          </ul>
        </el-collapse-item>
      </el-collapse>
      <el-empty v-if="!hubEntries.length" description="当前无已启用的报表模块" />
      <div v-else class="report-links">
        <router-link
          v-for="entry in hubEntries"
          :key="entry.path"
          :to="entry.path"
          class="report-link-card"
        >
          <el-icon :size="28"><component :is="iconOf(entry.icon)" /></el-icon>
          <span class="link-title">{{ entry.title }}</span>
          <span class="link-desc">{{ entry.description }}</span>
        </router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { DataLine } from '@element-plus/icons-vue'
import {
  DEV_PIPELINE_PREFERENCES,
  getReportHubPipelineSummary,
} from '../../config/mesDevPipelinePreferences.js'
import { resolveReportIcon } from '../../config/reportIcons.js'
import { getReportHubEntries } from '../../router/reportRoutes.js'

const hubEntries = computed(() => getReportHubEntries())
const pipelineSummary = getReportHubPipelineSummary()
const pipelinePreferences = DEV_PIPELINE_PREFERENCES
const prefsOpen = ref(['prefs'])

function iconOf(name) {
  return resolveReportIcon(name, DataLine)
}
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
  margin: 0 0 12px;
}

.prefs-collapse {
  margin-bottom: 16px;
  border: none;
}

.prefs-list {
  margin: 0;
  padding-left: 1.2em;
  color: var(--el-text-color-regular);
  font-size: 13px;
  line-height: 1.6;
}

.prefs-list li + li {
  margin-top: 8px;
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
