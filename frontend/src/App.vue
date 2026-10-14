<template>
  <router-view />
</template>

<script setup>
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html,
body,
#app {
  height: 100%;
  overflow: hidden;
}

body {
  font-family:
    'PingFang SC',
    'Microsoft YaHei',
    'Segoe UI',
    system-ui,
    -apple-system,
    sans-serif;
  background: #eef1f6;
  color: #303133;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

:root {
  --erp-content-bg: #eef1f6;
  --erp-card-radius: 8px;
  --erp-card-border: 1px solid #e8ecf1;
  --erp-card-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

/* 内容区滚动条更轻 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-thumb {
  background: rgba(144, 147, 153, 0.45);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(144, 147, 153, 0.7);
}

::-webkit-scrollbar-track {
  background: transparent;
}

/* Element Plus 卡片在列表页统一轻阴影 */
.el-card {
  --el-card-border-color: #e8ecf1;
  border-radius: var(--erp-card-radius);
}
</style>
