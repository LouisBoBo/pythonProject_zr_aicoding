<template>
  <div class="inbox-view">
    <section class="toolbar">
      <el-radio-group v-model="filters.level" @change="handleSearch">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="high">高</el-radio-button>
        <el-radio-button label="medium">中</el-radio-button>
        <el-radio-button label="low">低</el-radio-button>
      </el-radio-group>
      <el-input
        v-model="filters.keyword"
        placeholder="搜索标题或内容"
        clearable
        style="width: 220px"
        @keyup.enter="handleSearch"
      />
      <el-select v-model="filters.isRead" placeholder="阅读状态" clearable style="width: 120px">
        <el-option label="未读" :value="false" />
        <el-option label="已读" :value="true" />
      </el-select>
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
      <div class="toolbar-right">
        <el-button :disabled="!hasUnread" @click="handleMarkAllRead">全部已读</el-button>
      </div>
    </section>

    <section class="message-list" v-loading="loading">
      <div v-if="!loading && items.length === 0" class="empty-state">
        <el-icon :size="48"><Message /></el-icon>
        <p>暂无消息</p>
      </div>

      <article
        v-for="item in items"
        :key="item.id"
        class="message-card"
        :class="{ unread: !item.is_read }"
        @click="openDetail(item)"
      >
        <div class="card-left">
          <span class="category-tag" :class="'cat-' + item.category">
            {{ categoryLabel(item.category) }}
          </span>
          <h3 class="message-title">
            <span v-if="!item.is_read" class="unread-dot" />
            {{ item.title }}
          </h3>
          <p class="message-preview">{{ item.content }}</p>
          <div class="message-meta">
            <span v-if="item.source" class="meta-source">{{ item.source }}</span>
            <span class="meta-time">{{ formatTime(item.created_at) }}</span>
          </div>
        </div>
        <div class="card-right">
          <span class="level-tag" :class="'level-' + item.level">
            {{ levelLabel(item.level) }}
          </span>
          <el-button
            v-if="!item.is_read"
            link
            type="primary"
            @click.stop="handleMarkRead(item)"
          >
            标记已读
          </el-button>
        </div>
      </article>
    </section>

    <div v-if="total > 0" class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        background
        @size-change="loadList"
        @current-change="loadList"
      />
    </div>

    <el-drawer
      v-model="detailVisible"
      :title="detail?.title || '消息详情'"
      size="480px"
      destroy-on-close
    >
      <template v-if="detail">
        <div class="detail-tags">
          <span class="category-tag" :class="'cat-' + detail.category">
            {{ categoryLabel(detail.category) }}
          </span>
          <span class="level-tag" :class="'level-' + detail.level">
            {{ levelLabel(detail.level) }}
          </span>
        </div>
        <div class="detail-meta">
          <span v-if="detail.source">来源：{{ detail.source }}</span>
          <span>时间：{{ formatTime(detail.created_at) }}</span>
        </div>
        <div class="detail-content">{{ detail.content }}</div>
        <div v-if="detail.link" class="detail-actions">
          <el-button type="primary" @click="goLink(detail.link)">查看相关业务</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Message } from '@element-plus/icons-vue'
import {
  fetchMessageList,
  markAllMessagesRead,
  markMessageRead,
} from '../../api/messages'

const props = defineProps({
  category: { type: String, default: null },
  stats: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['refresh-stats'])

const router = useRouter()

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const detailVisible = ref(false)
const detail = ref(null)

const filters = reactive({
  keyword: '',
  isRead: null,
  level: '',
})

const hasUnread = computed(() => {
  if (props.category === 'system') return props.stats.system > 0
  if (props.category === 'alert') return props.stats.alert > 0
  if (props.category === 'announcement') return props.stats.announcement > 0
  return props.stats.total > 0
})

const CATEGORY_LABEL = {
  system: '系统通知',
  alert: '业务告警',
  announcement: '公告通知',
}

const LEVEL_LABEL = {
  high: '高',
  medium: '中',
  low: '低',
}

function categoryLabel(value) {
  return CATEGORY_LABEL[value] || value
}

function levelLabel(value) {
  return LEVEL_LABEL[value] || value
}

function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  const now = new Date()
  const diffMs = now - date
  const diffHours = diffMs / (1000 * 60 * 60)
  if (diffHours < 1) return '刚刚'
  if (diffHours < 24) return `${Math.floor(diffHours)} 小时前`
  if (diffHours < 48) return '昨天'
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchMessageList({
      page: page.value,
      pageSize: pageSize.value,
      category: props.category || undefined,
      level: filters.level || undefined,
      isRead: filters.isRead,
      keyword: filters.keyword.trim() || undefined,
    })
    items.value = data.items
    total.value = data.total
  } catch (err) {
    ElMessage.error(err.message || '加载消息失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.keyword = ''
  filters.isRead = null
  filters.level = ''
  page.value = 1
  loadList()
}

async function openDetail(item) {
  detail.value = item
  detailVisible.value = true
  if (!item.is_read) {
    await handleMarkRead(item, false)
  }
}

async function handleMarkRead(item, showToast = true) {
  try {
    const updated = await markMessageRead(item.id)
    item.is_read = updated.is_read
    if (detail.value?.id === item.id) {
      detail.value = updated
    }
    emit('refresh-stats')
    if (showToast) ElMessage.success('已标记为已读')
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  }
}

async function handleMarkAllRead() {
  try {
    await markAllMessagesRead({ category: props.category || undefined })
    ElMessage.success('已全部标记为已读')
    emit('refresh-stats')
    loadList()
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  }
}

function goLink(link) {
  detailVisible.value = false
  router.push(link)
}

watch(
  () => props.category,
  () => {
    page.value = 1
    loadList()
  },
  { immediate: true },
)
</script>

<style scoped>
.inbox-view {
  max-width: 960px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding: 14px 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.toolbar-right {
  margin-left: auto;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 200px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 0;
  color: var(--el-text-color-secondary);
}

.empty-state p {
  margin: 12px 0 0;
}

.message-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.message-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.message-card.unread {
  border-left: 3px solid var(--el-color-primary);
  background: #f8fbff;
}

.card-left {
  flex: 1;
  min-width: 0;
}

.card-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  flex-shrink: 0;
}

.category-tag {
  display: inline-block;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  margin-bottom: 6px;
}

.cat-system {
  background: #ecf5ff;
  color: #409eff;
}

.cat-alert {
  background: #fef0f0;
  color: #f56c6c;
}

.cat-announcement {
  background: #f0f9eb;
  color: #67c23a;
}

.level-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.level-high {
  background: #fef0f0;
  color: #f56c6c;
}

.level-medium {
  background: #fdf6ec;
  color: #e6a23c;
}

.level-low {
  background: #f0f9eb;
  color: #67c23a;
}

.message-title {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--el-color-primary);
  flex-shrink: 0;
}

.message-preview {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.message-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.detail-tags {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.detail-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 16px;
}

.detail-content {
  line-height: 1.7;
  color: var(--el-text-color-primary);
  white-space: pre-wrap;
}

.detail-actions {
  margin-top: 24px;
}
</style>
