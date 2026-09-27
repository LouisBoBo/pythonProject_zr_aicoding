<template>
  <div class="favorites-page">
    <header class="page-header">
      <div class="header-main">
        <h1 class="page-title">收藏夹</h1>
        <p class="page-sub">已收藏的网页与功能入口（按当前登录账号隔离，最多 {{ maxCount }} 条）</p>
      </div>
      <el-button :icon="Refresh" @click="loadList">刷新</el-button>
    </header>

    <section class="current-page-section" aria-label="当前页面信息">
      <h2 class="section-title">当前页面</h2>
      <el-descriptions :column="1" border size="small" class="current-page-info">
        <el-descriptions-item label="标题">{{ currentPageTitle }}</el-descriptions-item>
        <el-descriptions-item label="路径">
          <span class="url-cell">{{ currentPagePath }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <section v-loading="loading" class="table-section">
      <el-table v-if="items.length" :data="items" border style="width: 100%">
        <el-table-column prop="title" label="名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="url" label="网址 / 路径" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="url-cell">{{ row.url }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="收藏时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openFavorite(row)">打开</el-button>
            <el-button link type="danger" @click="confirmRemove(row)">取消收藏</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-else-if="!loading" class="empty-wrap">
        <el-empty description="暂无收藏网页">
          <p class="empty-hint">点击顶栏星标收藏页面后，将在此显示列表。</p>
        </el-empty>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { fetchCurrentUser } from '../../api/auth'
import {
  FAVORITES_MAX,
  favoritesStorageKey,
  readFavorites,
  removeFavoriteById,
} from '../../utils/pageFavorites'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const items = ref([])
const username = ref('')
const maxCount = FAVORITES_MAX

const currentPageTitle = computed(() => {
  const t = route.meta?.title
  return typeof t === 'string' && t.trim() ? t.trim() : '未命名'
})

const currentPagePath = computed(() => route.fullPath || route.path || '/')

function loadList() {
  loading.value = true
  try {
    items.value = readFavorites(username.value)
  } finally {
    loading.value = false
  }
}

function formatTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function isExternalUrl(url) {
  return /^https?:\/\//i.test(url)
}

function openFavorite(row) {
  const url = row?.url
  if (!url) return
  if (isExternalUrl(url)) {
    window.open(url, '_blank', 'noopener,noreferrer')
    return
  }
  router.push(url.startsWith('/') ? url : `/${url}`)
}

async function confirmRemove(row) {
  try {
    await ElMessageBox.confirm(`确定取消收藏「${row.title}」？`, '取消收藏', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  items.value = removeFavoriteById(username.value, row.id)
  ElMessage.success('已取消收藏')
}

function onStorageEvent(event) {
  if (event.key === favoritesStorageKey(username.value)) {
    loadList()
  }
}

onMounted(async () => {
  try {
    const user = await fetchCurrentUser()
    username.value = user?.username || ''
  } catch {
    username.value = ''
  }
  loadList()
  window.addEventListener('storage', onStorageEvent)
})

onUnmounted(() => {
  window.removeEventListener('storage', onStorageEvent)
})
</script>

<style scoped>
.favorites-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.page-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: #909399;
}

.current-page-section {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.section-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.table-section {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.url-cell {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  color: #606266;
}

.empty-wrap {
  padding: 24px 0 8px;
}

.empty-hint {
  margin: 8px 0 0;
  font-size: 13px;
  color: #909399;
}
</style>
