<template>
  <div class="ds-app">
    <aside class="ds-sidebar">
      <div class="ds-sidebar-head">
        <div class="ds-brand">
          <span class="ds-brand-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="22" height="22">
              <path
                fill="currentColor"
                d="M12 2c1.2 3.1 3.4 5.3 6.5 6.5-3.1 1.2-5.3 3.4-6.5 6.5-1.2-3.1-3.4-5.3-6.5-6.5C8.6 7.3 10.8 5.1 12 2Z"
              />
            </svg>
          </span>
          <span class="ds-brand-text">WorkBuddy</span>
        </div>
        <div class="ds-sidebar-tools">
          <button type="button" class="icon-btn" title="搜索会话" @click="ElMessage.info('会话搜索即将支持')">
            <el-icon><Search /></el-icon>
          </button>
        </div>
      </div>

      <button type="button" class="ds-new-chat" :disabled="streaming" @click="startNewChat">
        <el-icon><Plus /></el-icon>
        <span>开启新对话</span>
      </button>

      <div class="ds-history">
        <template v-for="group in historyGroups" :key="group.label">
          <div v-if="group.items.length" class="ds-history-label">{{ group.label }}</div>
          <button
            v-for="s in group.items"
            :key="s.id"
            type="button"
            class="ds-history-item"
            :class="{ active: s.id === activeSessionId }"
            @click="openSession(s.id)"
          >
            {{ s.title || '新对话' }}
          </button>
        </template>
      </div>

      <div class="ds-sidebar-foot">
        <div class="ds-user">
          <el-avatar :size="28" class="ds-user-avatar">{{ userInitial }}</el-avatar>
          <span class="ds-user-name">{{ username }}</span>
          <el-dropdown trigger="click" @command="onUserCommand">
            <button type="button" class="icon-btn">
              <el-icon><MoreFilled /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="open">打开 WorkBuddy 网页</el-dropdown-item>
                <el-dropdown-item command="refresh">刷新连接状态</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <p v-if="!meta.upstream_ok" class="ds-offline" title="点击刷新" @click="refreshMeta">
          引擎未连接{{ meta.upstream_detail ? `（${meta.upstream_detail}）` : '' }}
        </p>
      </div>
    </aside>

    <section class="ds-main">
      <header v-if="messages.length" class="ds-topbar">
        <h2 class="ds-chat-title">{{ chatTitle }}</h2>
        <a
          class="ds-topbar-link"
          :href="meta.web_url"
          target="_blank"
          rel="noopener noreferrer"
        >
          原站
        </a>
      </header>

      <div ref="threadEl" class="ds-thread" @scroll="onThreadScroll">
        <div v-if="!messages.length" class="ds-empty">
          <div class="ds-empty-logo" aria-hidden="true">
            <svg viewBox="0 0 48 48" width="44" height="44">
              <path
                fill="#4d6bfe"
                d="M24 4c2.4 6.2 6.8 10.6 13 13-6.2 2.4-10.6 6.8-13 13-2.4-6.2-6.8-10.6-13-13C17.2 14.6 21.6 10.2 24 4Z"
              />
            </svg>
          </div>
          <h1 class="ds-greeting">{{ greetingText }}</h1>
        </div>

        <div v-else class="ds-thread-inner">
          <article
            v-for="msg in messages"
            :key="msg.id"
            class="ds-msg"
            :class="msg.role === 'user' ? 'is-user' : 'is-assistant'"
          >
            <template v-if="msg.role === 'user'">
              <div class="ds-user-row">
                <div class="ds-user-bubble">{{ msg.text }}</div>
                <div class="ds-user-actions">
                  <button type="button" class="icon-btn sm" title="复制" @click="copyText(msg.text)">
                    <el-icon><CopyDocument /></el-icon>
                  </button>
                </div>
              </div>
            </template>
            <template v-else>
              <div class="ds-assistant-row">
                <div class="ds-assistant-avatar" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="18" height="18">
                    <path
                      fill="#4d6bfe"
                      d="M12 2c1.2 3.1 3.4 5.3 6.5 6.5-3.1 1.2-5.3 3.4-6.5 6.5-1.2-3.1-3.4-5.3-6.5-6.5C8.6 7.3 10.8 5.1 12 2Z"
                    />
                  </svg>
                </div>
                <div class="ds-assistant-body">
                  <div
                    v-if="msg.status || (msg.streaming && !msg.text && !msg.thinking)"
                    class="ds-live-status"
                  >
                    <span>{{ msg.status || statusHint || '正在处理…' }}</span>
                    <span v-if="msg.streaming" class="ds-cursor" />
                  </div>

                  <details
                    v-if="msg.thinking || (msg.streaming && msg.thinkStartedAt)"
                    class="ds-thinking"
                    :open="msg.streaming || thinkingExpanded[msg.id]"
                    @toggle="onThinkingToggle(msg.id, $event)"
                  >
                    <summary>
                      {{ thinkingSummary(msg) }}
                      <el-icon class="ds-chevron"><ArrowDown /></el-icon>
                    </summary>
                    <div class="ds-thinking-content">
                      <pre>{{ msg.thinking }}</pre>
                      <span v-if="msg.streaming && msg.thinking" class="ds-cursor" />
                    </div>
                  </details>

                  <div v-if="msg.text" class="ds-answer">
                    <div v-if="msg.streaming" class="ds-stream-plain">{{ msg.text }}</div>
                    <div v-else class="ds-md" v-html="renderMd(msg.text)" />
                    <span v-if="msg.streaming && msg.text" class="ds-cursor inline" />
                  </div>
                </div>
              </div>
            </template>
          </article>
        </div>
      </div>

      <button
        v-if="showScrollDown"
        type="button"
        class="ds-scroll-down"
        @click="scrollToBottom(true)"
      >
        <el-icon><ArrowDown /></el-icon>
      </button>

      <div class="ds-composer-wrap">
        <div class="ds-composer">
          <textarea
            ref="inputEl"
            v-model="inputText"
            class="ds-input"
            rows="1"
            placeholder="给 WorkBuddy 发送消息"
            @keydown="onComposerKeydown"
            @input="resizeInput"
          />
          <div class="ds-composer-bar">
            <div class="ds-modes">
              <button
                type="button"
                class="ds-mode"
                :class="{ active: modeDeepThink }"
                @click="modeDeepThink = !modeDeepThink"
              >
                <el-icon><Cpu /></el-icon>
                深度思考
              </button>
              <button
                type="button"
                class="ds-mode"
                :class="{ active: modeSmartSearch }"
                @click="modeSmartSearch = !modeSmartSearch"
              >
                <el-icon><Search /></el-icon>
                智能搜索
              </button>
            </div>
            <div class="ds-composer-actions">
              <button type="button" class="icon-btn" title="附件" @click="ElMessage.info('附件上传即将支持')">
                <el-icon><Paperclip /></el-icon>
              </button>
              <button
                v-if="streaming"
                type="button"
                class="ds-send is-stop active"
                title="停止生成"
                @click="onStopStream"
              >
                <el-icon><VideoPause /></el-icon>
              </button>
              <button
                v-else
                type="button"
                class="ds-send"
                :class="{ active: canSend }"
                :disabled="!canSend"
                @click="onSend"
              >
                <el-icon><Top /></el-icon>
              </button>
            </div>
          </div>
        </div>
        <p v-if="errorText" class="ds-error">{{ errorText }}</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch, triggerRef } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowDown,
  CopyDocument,
  Cpu,
  MoreFilled,
  Paperclip,
  Plus,
  Search,
  Top,
  VideoPause,
} from '@element-plus/icons-vue'
import { fetchCurrentUser } from '../../api/auth'
import { consumeChatStream, fetchWorkBuddyMeta } from '../../api/workbuddy'
import { renderMarkdownLite, normalizeAssistantText } from '../../utils/markdownLite'
import { attachSmoothDisplay, takeStreamIncrement } from '../../utils/streamReveal'

const STORAGE_KEY = 'erp-workbuddy-sessions-v1'

let msgSeq = 0
function nextId() {
  msgSeq += 1
  return `m-${msgSeq}`
}

const meta = reactive({
  upstream_ok: false,
  web_url: 'http://127.0.0.1:3081',
  upstream: '',
  upstream_detail: '',
})

const sessions = ref([])
const activeSessionId = ref('')
const messages = ref([])
const inputText = ref('')
const streaming = ref(false)
const statusHint = ref('')
const errorText = ref('')
const threadEl = ref(null)
const inputEl = ref(null)
const showScrollDown = ref(false)
const thinkingExpanded = reactive({})
const username = ref('用户')
const modeDeepThink = ref(true)
const modeSmartSearch = ref(true)

let abortCtrl = null
let scrollPinned = true
let metaTimer = null

function onWindowFocus() {
  refreshMeta()
}

const userInitial = computed(() => (username.value || '用').charAt(0).toUpperCase())

const canSend = computed(() => !!inputText.value.trim() && !streaming.value)

const chatTitle = computed(() => {
  const first = messages.value.find((m) => m.role === 'user')
  if (!first) return '新对话'
  const t = first.text.trim()
  return t.length > 28 ? `${t.slice(0, 28)}…` : t
})

const greetingText = computed(() => {
  const h = new Date().getHours()
  let part = '你好'
  if (h >= 5 && h < 12) part = '早上好'
  else if (h >= 12 && h < 18) part = '下午好'
  else part = '晚上好'
  return `${part}，今天想做点什么？`
})

const historyGroups = computed(() => {
  const now = Date.now()
  const day = 86400000
  const buckets = { today: [], yesterday: [], week: [], older: [] }
  const sorted = [...sessions.value].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0))
  for (const s of sorted) {
    const age = now - (s.updatedAt || s.createdAt || now)
    if (age < day) buckets.today.push(s)
    else if (age < day * 2) buckets.yesterday.push(s)
    else if (age < day * 7) buckets.week.push(s)
    else buckets.older.push(s)
  }
  return [
    { label: '今天', items: buckets.today },
    { label: '昨天', items: buckets.yesterday },
    { label: '7 天内', items: buckets.week },
    { label: '更早', items: buckets.older },
  ]
})

function loadSessions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const data = JSON.parse(raw)
    if (Array.isArray(data)) sessions.value = data
  } catch {
    sessions.value = []
  }
}

function saveSessions() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions.value))
}

function persistActiveSession() {
  if (!activeSessionId.value) return
  const idx = sessions.value.findIndex((s) => s.id === activeSessionId.value)
  const title =
    messages.value.find((m) => m.role === 'user')?.text?.trim().slice(0, 40) || '新对话'
  const payload = {
    id: activeSessionId.value,
    title,
    createdAt: idx >= 0 ? sessions.value[idx].createdAt : Date.now(),
    updatedAt: Date.now(),
    messages: messages.value.map(cloneMessage),
  }
  if (idx >= 0) sessions.value[idx] = payload
  else sessions.value.unshift(payload)
  saveSessions()
}

function cloneMessage(m) {
  return {
    id: m.id,
    role: m.role,
    text: m.text,
    thinking: m.thinking,
    status: m.status,
    streaming: false,
    thinkStartedAt: m.thinkStartedAt,
    thinkEndedAt: m.thinkEndedAt,
  }
}

function ensureSession() {
  if (activeSessionId.value) return
  activeSessionId.value = `s-${Date.now()}`
}

function startNewChat() {
  if (streaming.value) return
  persistActiveSession()
  activeSessionId.value = ''
  messages.value = []
  errorText.value = ''
  statusHint.value = ''
  inputText.value = ''
  nextTick(resizeInput)
}

function openSession(id) {
  if (streaming.value) return
  persistActiveSession()
  const s = sessions.value.find((x) => x.id === id)
  if (!s) return
  activeSessionId.value = s.id
  messages.value = (s.messages || []).map(cloneMessage)
  errorText.value = ''
  scrollPinned = true
  nextTick(() => scrollToBottom(true))
}

function renderMd(text) {
  return renderMarkdownLite(text)
}

function thinkingSummary(msg) {
  if (msg.streaming && !msg.thinkEndedAt) {
    const sec = msg.thinkStartedAt
      ? Math.max(1, Math.round((Date.now() - msg.thinkStartedAt) / 1000))
      : null
    return sec ? `思考中（${sec} 秒）` : '思考中'
  }
  const sec =
    msg.thinkStartedAt && msg.thinkEndedAt
      ? Math.max(1, Math.round((msg.thinkEndedAt - msg.thinkStartedAt) / 1000))
      : 1
  return `已思考（用时 ${sec} 秒）`
}

function onThinkingToggle(id, event) {
  thinkingExpanded[id] = event.target.open
}

async function scrollToBottom(force = false) {
  if (!force && !scrollPinned) return
  await nextTick()
  const el = threadEl.value
  if (!el) return
  el.scrollTop = el.scrollHeight
  showScrollDown.value = false
}

function onThreadScroll() {
  const el = threadEl.value
  if (!el) return
  const dist = el.scrollHeight - el.scrollTop - el.clientHeight
  scrollPinned = dist < 80
  showScrollDown.value = dist > 120
}

function resizeInput() {
  const el = inputEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 160)}px`
}

async function refreshMeta() {
  try {
    const data = await fetchWorkBuddyMeta()
    meta.upstream_ok = !!data.upstream_ok
    meta.web_url = data.web_url || meta.web_url
    meta.upstream = data.upstream || ''
    meta.upstream_detail = data.upstream_detail || ''
  } catch (e) {
    meta.upstream_ok = false
    meta.upstream_detail = e.message || String(e)
  }
}

async function loadUser() {
  try {
    const u = await fetchCurrentUser()
    username.value = u?.username || '用户'
  } catch {
    username.value = '用户'
  }
}

function stopStream() {
  if (abortCtrl) {
    abortCtrl.abort()
  }
}

function onStopStream() {
  if (!streaming.value) return
  stopStream()
}

function onComposerKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    onSend()
  }
}

function appendAssistantShell() {
  const item = reactive({
    id: nextId(),
    role: 'assistant',
    text: '',
    thinking: '',
    status: '',
    streaming: true,
    thinkStartedAt: Date.now(),
    thinkEndedAt: null,
  })
  messages.value.push(item)
  return item
}

function createMessageStreamers(assistant) {
  let uiFlushScheduled = false
  const touch = () => {
    if (uiFlushScheduled) return
    uiFlushScheduled = true
    requestAnimationFrame(() => {
      uiFlushScheduled = false
      triggerRef(messages)
      scrollToBottom()
    })
  }
  const touchNow = () => {
    uiFlushScheduled = false
    triggerRef(messages)
    scrollToBottom(true)
  }
  const server = { reply: '', thinking: '' }
  const smoothReply = attachSmoothDisplay(assistant, 'text', { charsPerFrame: 14, onFrame: touch })
  const smoothThink = attachSmoothDisplay(assistant, 'thinking', { charsPerFrame: 14, onFrame: touch })

  function appendField(serverKey, smooth, field, chunk) {
    const result = takeStreamIncrement(server[serverKey], chunk)
    server[serverKey] = result.accum
    if (result.replace) {
      assistant[field] = result.accum
      smooth.setTarget(result.accum)
      smooth.flush()
      touchNow()
      return
    }
    if (result.increment) smooth.setTarget(result.accum)
  }

  return {
    server,
    appendReply: (chunk) => appendField('reply', smoothReply, 'text', chunk),
    appendThinking: (chunk) => appendField('thinking', smoothThink, 'thinking', chunk),
    syncReply(full) {
      const text = normalizeAssistantText(full)
      if (!text) return
      server.reply = text
      smoothReply.setTarget(text)
      smoothReply.flush()
      touchNow()
    },
    syncThinking(full) {
      const text = normalizeAssistantText(full)
      if (!text) return
      server.thinking = text
      smoothThink.setTarget(text)
      smoothThink.flush()
      touchNow()
    },
    finishSmooth() {
      smoothReply.flush()
      smoothThink.flush()
    },
    finished: () => Promise.resolve(),
  }
}

function handleStreamEvent(evt, assistant, streamers) {
  const type = evt.type
  if (type === 'status') {
    const chunk = evt.detail || evt.message || evt.delta || ''
    if (chunk) {
      assistant.status = chunk
      statusHint.value = chunk
    }
    if (!assistant.thinkStartedAt) assistant.thinkStartedAt = Date.now()
    return
  }
  if (type === 'thinking') {
    if (!assistant.thinkStartedAt) assistant.thinkStartedAt = Date.now()
    streamers.appendThinking(evt.delta || evt.text || '')
    return
  }
  if (type === 'reply') {
    if (assistant.thinking && !assistant.thinkEndedAt) {
      assistant.thinkEndedAt = Date.now()
    }
    streamers.appendReply(evt.delta || evt.text || '')
    return
  }
  if (type === 'done') {
    if (evt.thinking) streamers.syncThinking(evt.thinking)
    if (evt.reply) streamers.syncReply(evt.reply)
    if (!assistant.thinkEndedAt && assistant.thinkStartedAt) {
      assistant.thinkEndedAt = Date.now()
    }
    assistant.status = ''
    statusHint.value = ''
    return
  }
  if (type === 'error') {
    throw new Error(evt.message || evt.detail || 'WorkBuddy 返回错误')
  }
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

function onUserCommand(cmd) {
  if (cmd === 'open') window.open(meta.web_url, '_blank', 'noopener,noreferrer')
  if (cmd === 'refresh') refreshMeta()
}

async function onSend() {
  const text = inputText.value.trim()
  if (!text || streaming.value) return

  ensureSession()
  errorText.value = ''
  statusHint.value = ''
  messages.value.push({ id: nextId(), role: 'user', text })
  inputText.value = ''
  resizeInput()
  scrollPinned = true
  await scrollToBottom(true)

  const assistant = appendAssistantShell()
  const streamers = createMessageStreamers(assistant)
  await scrollToBottom(true)

  streaming.value = true
  abortCtrl = new AbortController()

  let tickTimer = null
  const bumpThinkingLabel = () => {
    if (!assistant.streaming) return
    scrollToBottom()
  }
  tickTimer = window.setInterval(bumpThinkingLabel, 500)

  try {
    await consumeChatStream(
      text,
      (evt) => {
        handleStreamEvent(evt, assistant, streamers)
      },
      abortCtrl.signal,
    )
    streamers.finishSmooth()
    assistant.streaming = false
    streaming.value = false
    assistant.status = ''
    statusHint.value = ''
    if (!assistant.text && !assistant.thinking) {
      assistant.text = '（无文本回复）'
    }
    if (!assistant.thinkEndedAt && assistant.thinkStartedAt) {
      assistant.thinkEndedAt = Date.now()
    }
    persistActiveSession()
  } catch (e) {
    if (e.name === 'AbortError') {
      streamers.finishSmooth()
      assistant.streaming = false
      streaming.value = false
      assistant.status = ''
      statusHint.value = ''
      if (!assistant.text && !assistant.thinking) {
        assistant.text = '（已停止）'
      }
      persistActiveSession()
      return
    }
    const errMsg = e.message || String(e)
    errorText.value = errMsg
    assistant.streaming = false
    streaming.value = false
    if (!assistant.text) assistant.text = `请求失败：${errMsg}`
    ElMessage.error(errMsg)
    persistActiveSession()
  } finally {
    if (tickTimer) window.clearInterval(tickTimer)
    abortCtrl = null
    await scrollToBottom(true)
  }
}

watch(
  () => messages.value.length,
  () => {
    if (!messages.value.length) return
    persistActiveSession()
  },
)

onMounted(() => {
  loadSessions()
  refreshMeta()
  loadUser()
  resizeInput()
  window.addEventListener('focus', onWindowFocus)
  metaTimer = window.setInterval(refreshMeta, 15000)
})

onBeforeUnmount(() => {
  persistActiveSession()
  stopStream()
  window.removeEventListener('focus', onWindowFocus)
  if (metaTimer) window.clearInterval(metaTimer)
})
</script>

<style scoped>
.ds-app {
  --ds-blue: #4d6bfe;
  --ds-bg: #ffffff;
  --ds-sidebar: #f9fafb;
  --ds-border: #e5e7eb;
  --ds-text: #1f2937;
  --ds-muted: #6b7280;
  --ds-user-bubble: #edf2ff;
  margin: -16px -20px;
  width: calc(100% + 40px);
  height: calc(100vh - 48px);
  min-height: 520px;
  display: flex;
  background: var(--ds-bg);
  color: var(--ds-text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei',
    sans-serif;
}

.ds-sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--ds-sidebar);
  border-right: 1px solid var(--ds-border);
  padding: 12px 10px 10px;
}

.ds-sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 6px 10px;
}

.ds-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ds-blue);
  font-weight: 600;
  font-size: 18px;
}

.ds-brand-icon {
  display: inline-flex;
}

.ds-sidebar-tools {
  display: flex;
  gap: 4px;
}

.icon-btn {
  border: none;
  background: transparent;
  color: var(--ds-muted);
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.icon-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: var(--ds-text);
}

.icon-btn.sm {
  width: 28px;
  height: 28px;
}

.ds-new-chat {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  border: 1px solid var(--ds-border);
  background: #fff;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 14px;
  cursor: pointer;
  margin-bottom: 10px;
}

.ds-new-chat:hover:not(:disabled) {
  background: #f3f4f6;
}

.ds-new-chat:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ds-history {
  flex: 1;
  overflow: auto;
  padding: 0 4px;
}

.ds-history-label {
  font-size: 12px;
  color: var(--ds-muted);
  padding: 10px 8px 4px;
}

.ds-history-item {
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  border-radius: 10px;
  padding: 9px 10px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ds-history-item:hover,
.ds-history-item.active {
  background: #e8eeff;
  color: #1e3a8a;
}

.ds-sidebar-foot {
  border-top: 1px solid var(--ds-border);
  padding-top: 10px;
}

.ds-user {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
}

.ds-user-avatar {
  background: var(--ds-blue);
  color: #fff;
  font-size: 12px;
}

.ds-user-name {
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ds-offline {
  margin: 6px 8px 0;
  font-size: 11px;
  color: #dc2626;
  cursor: pointer;
  line-height: 1.35;
}

.ds-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  position: relative;
  background: #fff;
}

.ds-topbar {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  border-bottom: 1px solid #f3f4f6;
  padding: 0 16px;
}

.ds-chat-title {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  max-width: 70%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ds-topbar-link {
  position: absolute;
  right: 16px;
  font-size: 12px;
  color: var(--ds-muted);
  text-decoration: none;
}

.ds-topbar-link:hover {
  color: var(--ds-blue);
}

.ds-thread {
  flex: 1;
  overflow: auto;
  padding: 24px 0 12px;
}

.ds-empty {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding-bottom: 120px;
}

.ds-greeting {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.ds-thread-inner {
  max-width: 820px;
  margin: 0 auto;
  padding: 0 24px 140px;
}

.ds-msg {
  margin-bottom: 28px;
}

.ds-user-row {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.ds-user-bubble {
  max-width: min(100%, 640px);
  background: var(--ds-user-bubble);
  color: #111827;
  padding: 12px 16px;
  border-radius: 18px;
  font-size: 15px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.ds-user-actions {
  display: flex;
  gap: 2px;
  margin-top: 6px;
  opacity: 0;
  transition: opacity 0.15s;
}

.ds-user-row:hover .ds-user-actions {
  opacity: 1;
}

.ds-assistant-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.ds-assistant-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #eef2ff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ds-assistant-body {
  flex: 1;
  min-width: 0;
  font-size: 15px;
  line-height: 1.65;
}

.ds-live-status {
  color: var(--ds-muted);
  font-size: 14px;
  margin-bottom: 8px;
}

.ds-thinking {
  margin-bottom: 10px;
  border-left: 2px solid #e5e7eb;
  padding-left: 12px;
}

.ds-thinking summary {
  list-style: none;
  cursor: pointer;
  color: var(--ds-muted);
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  user-select: none;
}

.ds-thinking summary::-webkit-details-marker {
  display: none;
}

.ds-chevron {
  transition: transform 0.15s;
}

.ds-thinking[open] .ds-chevron {
  transform: rotate(180deg);
}

.ds-thinking-content pre {
  margin: 8px 0 0;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 14px;
  color: #4b5563;
}

.ds-md :deep(pre) {
  background: #f3f4f6;
  border-radius: 8px;
  padding: 10px 12px;
  overflow: auto;
  font-size: 13px;
}

.ds-stream-plain {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 15px;
  line-height: 1.65;
  color: #1f2937;
}

.ds-md :deep(p) {
  margin: 0 0 10px;
}

.ds-md :deep(ul),
.ds-md :deep(ol) {
  margin: 0 0 12px 1.2em;
  padding: 0;
}

.ds-md :deep(li) {
  margin: 4px 0;
}

.ds-md :deep(h3),
.ds-md :deep(h4) {
  margin: 12px 0 8px;
  font-size: 15px;
}

.ds-md :deep(table.md-table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 14px;
  font-size: 13px;
}

.ds-md :deep(table.md-table th),
.ds-md :deep(table.md-table td) {
  border: 1px solid #e5e7eb;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

.ds-md :deep(table.md-table th) {
  background: #f9fafb;
  font-weight: 600;
}

.ds-md :deep(table.md-table tr:nth-child(even) td) {
  background: #fafafa;
}

.ds-md :deep(code) {
  background: #f3f4f6;
  padding: 1px 4px;
  border-radius: 4px;
  font-size: 0.92em;
}

.ds-cursor {
  display: inline-block;
  width: 6px;
  height: 1em;
  margin-left: 2px;
  vertical-align: text-bottom;
  background: var(--ds-blue);
  animation: ds-blink 1s step-end infinite;
}

.ds-cursor.inline {
  height: 16px;
}

@keyframes ds-blink {
  50% {
    opacity: 0;
  }
}

.ds-scroll-down {
  position: absolute;
  right: 24px;
  bottom: 150px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--ds-border);
  background: #fff;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 2;
}

.ds-composer-wrap {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 0 24px 20px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, #fff 28%);
}

.ds-composer {
  max-width: 820px;
  margin: 0 auto;
  border: 1px solid var(--ds-border);
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.08);
  padding: 14px 16px 12px;
}

.ds-input {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  font-size: 15px;
  line-height: 1.5;
  min-height: 28px;
  max-height: 160px;
  font-family: inherit;
  color: var(--ds-text);
}

.ds-input::placeholder {
  color: #9ca3af;
}

.ds-composer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
}

.ds-modes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ds-mode {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--ds-border);
  background: #fff;
  color: #374151;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
}

.ds-mode.active {
  background: #eef2ff;
  border-color: #c7d2fe;
  color: #1d4ed8;
}

.ds-composer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ds-send {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: #d1d5db;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: not-allowed;
}

.ds-send.active {
  background: var(--ds-blue);
  cursor: pointer;
}

.ds-send.active:hover {
  filter: brightness(1.05);
}

.ds-send.is-stop.active {
  background: #dc2626;
  cursor: pointer;
}

.ds-error {
  max-width: 820px;
  margin: 8px auto 0;
  font-size: 12px;
  color: #dc2626;
  text-align: center;
}

@media (max-width: 960px) {
  .ds-sidebar {
    display: none;
  }
  .ds-greeting {
    font-size: 22px;
  }
}
</style>
