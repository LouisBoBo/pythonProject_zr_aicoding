<template>
  <div class="cc-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">Cursor 写码过程</h1>
        <p class="page-sub">
          真实工程内完整过程记录：Thinking / 工具 / 正文交错显示；记录落盘到
          <code>docs/cursor-coding-runs/</code>
        </p>
      </div>
      <div class="header-actions">
        <el-tag :type="meta.upstream_ok ? 'success' : 'danger'" effect="plain">
          上游 {{ meta.upstream_ok ? '已连接' : '未连接' }}
        </el-tag>
        <el-button @click="refreshMeta">刷新状态</el-button>
        <el-button type="primary" :loading="starting" @click="onStart">确认开写</el-button>
      </div>
    </header>

    <el-alert
      v-if="!meta.upstream_ok"
      type="warning"
      :closable="false"
      show-icon
      title="请先启动 Cursor 写码本机服务"
      description="在 dsh-cursor-coding 目录执行：pnpm ui 。默认地址 http://127.0.0.1:18788"
      style="margin-bottom: 14px"
    />

    <div class="layout">
      <aside class="side panel">
        <h3>开工参数</h3>
        <el-form label-position="top">
          <el-form-item label="工程路径">
            <el-input v-model="form.workspace" />
          </el-form-item>
          <el-form-item label="写码诉求">
            <el-input v-model="form.requirement" type="textarea" :rows="5" />
          </el-form-item>
          <el-form-item label="可写范围（可选）">
            <el-input v-model="form.writeScopeText" placeholder="_dsh_cursor_coding_bc_probe.txt" />
          </el-form-item>
          <div class="side-actions">
            <el-button @click="onPrepareProbe">准备探针文件</el-button>
            <el-button @click="loadLocalRuns">刷新记录</el-button>
          </div>
        </el-form>

        <h3 style="margin-top: 18px">本工程过程记录</h3>
        <el-empty v-if="!localRuns.length" description="尚无落盘记录" :image-size="64" />
        <ul v-else class="run-list">
          <li
            v-for="r in localRuns"
            :key="r.job_id"
            :class="{ active: r.job_id === currentJobId }"
            @click="openLocalRun(r.job_id)"
          >
            <div class="run-id">{{ r.job_id }}</div>
            <div class="run-meta">
              {{ r.status }} · 正文 {{ r.assistant_chars }} · 思考 {{ r.thinking_chars }} · 片段
              {{ r.transcript_count }}
            </div>
          </li>
        </ul>
      </aside>

      <section class="main panel">
        <div class="main-meta">
          <div>
            <el-tag size="small">{{ statusLabel || 'idle' }}</el-tag>
            <span class="job-line">{{ currentJobId || '尚未开工' }} · 片段 {{ transcript.length }}</span>
          </div>
          <div>
            <el-button size="small" @click="copyDialog">复制对话</el-button>
            <el-button size="small" @click="showRaw = !showRaw">{{ showRaw ? '隐藏' : '原始' }} JSON</el-button>
          </div>
        </div>

        <div ref="dialogEl" class="dialog">
          <p v-if="!transcript.length" class="hint">等待 Cursor 过程输出…</p>
          <div v-for="it in transcript" :key="it.id" class="bubble" :class="it.kind">
            <template v-if="it.kind === 'user'">
              <div class="role">You</div>
              <pre class="body">{{ it.text }}</pre>
            </template>
            <template v-else-if="it.kind === 'thinking'">
              <details :open="!!it.streaming">
                <summary>Thinking{{ it.streaming ? ' …' : '' }}</summary>
                <pre class="body">{{ it.text }}</pre>
              </details>
            </template>
            <template v-else-if="it.kind === 'tool'">
              <span>⚙ {{ it.name }} · {{ it.tool_status }} · {{ it.path }}</span>
            </template>
            <template v-else-if="it.kind === 'assistant'">
              <div class="role">Cursor</div>
              <div class="body md" v-html="renderMd(it.text)" />
            </template>
            <template v-else-if="it.kind === 'status'">
              <em>{{ it.text }}</em>
            </template>
          </div>
        </div>

        <div class="bottom-grid">
          <div>
            <h3>追问</h3>
            <el-input v-model="steerText" type="textarea" :rows="3" placeholder="再说一句…" />
            <el-button style="margin-top: 8px" :disabled="!currentJobId" @click="onSteer">发给 Cursor</el-button>
          </div>
          <div>
            <h3>审后同步</h3>
            <div v-if="!reviewFiles.length" class="hint">尚无待审文件</div>
            <el-checkbox-group v-else v-model="accepted">
              <div v-for="f in reviewFiles" :key="f.path" class="check-row">
                <el-checkbox :label="f.path">{{ f.path }} <el-tag size="small">{{ f.tag }}</el-tag></el-checkbox>
              </div>
            </el-checkbox-group>
            <el-button type="primary" style="margin-top: 8px" :disabled="!currentJobId" @click="onApply">
              同步到本机
            </el-button>
          </div>
        </div>

        <p v-if="msg" class="msg" :class="{ err: msgErr }">{{ msg }}</p>
        <p v-if="savedPath" class="hint">已落盘：{{ savedPath }}</p>
        <pre v-if="showRaw" class="raw">{{ rawJson }}</pre>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  applyJob,
  confirmCursorJob,
  consumeJobStream,
  fetchCursorMeta,
  fetchJobDialog,
  getLocalRun,
  listLocalRuns,
  prepareProbe,
  steerJob,
} from '../../api/cursorCoding'

const meta = reactive({
  upstream_ok: false,
  upstream: 'http://127.0.0.1:18788',
  project_root: '',
  default_requirement: '',
})

const form = reactive({
  workspace: '',
  requirement: '',
  writeScopeText: '_dsh_cursor_coding_bc_probe.txt',
})

const localRuns = ref([])
const currentJobId = ref('')
const statusLabel = ref('idle')
const transcript = ref([])
const review = reactive({ inScope: [], deleted: [], deferred: [] })
const accepted = ref([])
const steerText = ref('')
const starting = ref(false)
const msg = ref('')
const msgErr = ref(false)
const savedPath = ref('')
const showRaw = ref(false)
const rawJson = ref('')
const dialogEl = ref(null)

let abortStream = null
let pollTimer = null

const reviewFiles = computed(() => {
  const out = []
  ;(review.inScope || []).forEach((p) => out.push({ path: p, tag: '改' }))
  ;(review.deleted || []).forEach((p) => out.push({ path: p, tag: '删' }))
  ;(review.deferred || []).forEach((p) => out.push({ path: p, tag: '外' }))
  return out
})

function setMsg(text, err = false) {
  msg.value = text
  msgErr.value = err
}

function escapeHtml(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function renderMd(text) {
  let esc = escapeHtml(text)
  esc = esc.replace(/^##\s+(.+)$/gm, '<h3>$1</h3>')
  esc = esc.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  esc = esc.replace(/`([^`]+)`/g, '<code>$1</code>')
  return esc.replace(/\n/g, '<br/>')
}

function applyReviewFromSnapshot(data) {
  review.inScope = data.review_in_scope || []
  review.deleted = data.review_deleted || []
  review.deferred = data.review_deferred || []
  accepted.value = [...(review.inScope || []), ...(review.deleted || [])]
}

function stopStream() {
  if (abortStream) {
    abortStream.abort()
    abortStream = null
  }
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function refreshMeta() {
  try {
    const data = await fetchCursorMeta()
    Object.assign(meta, data)
    if (!form.workspace) form.workspace = data.project_root || ''
    if (!form.requirement) form.requirement = data.default_requirement || ''
  } catch (e) {
    setMsg(String(e.message || e), true)
  }
}

async function loadLocalRuns() {
  try {
    const data = await listLocalRuns()
    localRuns.value = data.items || []
  } catch (e) {
    setMsg(String(e.message || e), true)
  }
}

async function pullDialog(jobId) {
  const data = await fetchJobDialog(jobId)
  transcript.value = data.transcript || []
  statusLabel.value = data.status || ''
  savedPath.value = data.saved_md_path || ''
  rawJson.value = JSON.stringify(data, null, 2)
  if (data.status === 'pending_review') applyReviewFromSnapshot(data)
  await nextTick()
  if (dialogEl.value) dialogEl.value.scrollTop = dialogEl.value.scrollHeight
  return data
}

async function openLocalRun(jobId) {
  stopStream()
  currentJobId.value = jobId
  try {
    const data = await getLocalRun(jobId)
    transcript.value = data.transcript || []
    statusLabel.value = data.status || 'saved'
    savedPath.value = data.md_path || ''
    rawJson.value = JSON.stringify(data, null, 2)
    applyReviewFromSnapshot(data)
    setMsg('已加载本工程落盘记录 ' + jobId)
  } catch (e) {
    setMsg(String(e.message || e), true)
  }
}

async function startWatch(jobId) {
  stopStream()
  currentJobId.value = jobId
  abortStream = new AbortController()
  // 轮询兜底：保证 transcript / 落盘更新
  pollTimer = setInterval(async () => {
    try {
      const d = await pullDialog(jobId)
      if (['succeeded', 'failed', 'cancelled'].includes(d.status)) {
        stopStream()
        await loadLocalRuns()
      }
    } catch {
      /* ignore poll errors while streaming */
    }
  }, 1200)

  try {
    await consumeJobStream(
      jobId,
      (ev) => {
        if (ev.type === 'snapshot') {
          if (Array.isArray(ev.transcript)) transcript.value = ev.transcript
          statusLabel.value = ev.status || statusLabel.value
          if (ev.status === 'pending_review') {
            applyReviewFromSnapshot(ev)
          }
          nextTick(() => {
            if (dialogEl.value) dialogEl.value.scrollTop = dialogEl.value.scrollHeight
          })
        }
        if (ev.type === 'done') {
          statusLabel.value = ev.status || 'done'
          pullDialog(jobId).then(() => loadLocalRuns())
          stopStream()
        }
        if (ev.type === 'error') setMsg(ev.message || '流错误', true)
      },
      abortStream.signal,
    )
  } catch (e) {
    if (e.name !== 'AbortError') setMsg(String(e.message || e), true)
  }
}

async function onPrepareProbe() {
  try {
    const data = await prepareProbe()
    ElMessage.success('探针已写入：' + data.path)
  } catch (e) {
    setMsg(String(e.message || e), true)
  }
}

async function onStart() {
  starting.value = true
  setMsg('')
  try {
    await onPrepareProbe()
    const write_scope = String(form.writeScopeText || '')
      .split(/[\n,]+/)
      .map((s) => s.trim())
      .filter(Boolean)
    const data = await confirmCursorJob({
      workspace: form.workspace,
      requirement: form.requirement,
      write_scope,
    })
    transcript.value = []
    setMsg('已开工 ' + data.job_id)
    await startWatch(data.job_id)
  } catch (e) {
    setMsg(String(e.message || e), true)
  } finally {
    starting.value = false
  }
}

async function onSteer() {
  try {
    if (!currentJobId.value) throw new Error('无任务')
    if (!steerText.value.trim()) throw new Error('请输入追问')
    await steerJob(currentJobId.value, steerText.value.trim())
    steerText.value = ''
    setMsg('追问已发送')
    await startWatch(currentJobId.value)
  } catch (e) {
    setMsg(String(e.message || e), true)
  }
}

async function onApply() {
  try {
    if (!currentJobId.value) throw new Error('无任务')
    const data = await applyJob(currentJobId.value, accepted.value)
    setMsg('已同步：' + ((data.synced_files || []).join(', ') || '无文件'))
    await pullDialog(currentJobId.value)
    await loadLocalRuns()
  } catch (e) {
    setMsg(String(e.message || e), true)
  }
}

async function copyDialog() {
  const parts = []
  transcript.value.forEach((it) => {
    if (it.kind === 'thinking') parts.push('【Thinking】\n' + (it.text || ''))
    if (it.kind === 'assistant') parts.push('【Assistant】\n' + (it.text || ''))
    if (it.kind === 'user') parts.push('【You】\n' + (it.text || ''))
    if (it.kind === 'tool') parts.push('【Tool】' + (it.name || '') + ' ' + (it.path || ''))
  })
  try {
    await navigator.clipboard.writeText(parts.join('\n\n'))
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

watch(transcript, async () => {
  await nextTick()
  if (dialogEl.value) dialogEl.value.scrollTop = dialogEl.value.scrollHeight
})

onMounted(async () => {
  await refreshMeta()
  await loadLocalRuns()
})

onBeforeUnmount(() => stopStream())
</script>

<style scoped>
.cc-page {
  padding: 4px 2px 28px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 14px;
}
.page-title {
  margin: 0;
  font-size: 22px;
}
.page-sub {
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 14px;
}
@media (max-width: 1100px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
.panel {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 14px;
}
.side h3,
.main h3 {
  margin: 0 0 10px;
  font-size: 14px;
}
.side-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.run-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 360px;
  overflow: auto;
}
.run-list li {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
  margin-bottom: 8px;
  cursor: pointer;
}
.run-list li.active,
.run-list li:hover {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.run-id {
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.run-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}
.main-meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
}
.job-line {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.dialog {
  height: min(58vh, 640px);
  overflow: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  padding: 12px;
  background: var(--el-fill-color-blank);
}
.hint {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.bubble {
  margin: 0 0 12px;
}
.bubble .role {
  font-size: 11px;
  opacity: 0.65;
  margin-bottom: 4px;
  text-transform: uppercase;
}
.bubble.user .body,
.bubble.thinking .body {
  white-space: pre-wrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  margin: 0;
  padding: 10px;
  border-radius: 10px;
  background: var(--el-fill-color-light);
}
.bubble.thinking details {
  border: 1px dashed var(--el-border-color);
  border-radius: 10px;
  padding: 8px 10px;
  background: #f8f5ff;
}
.bubble.tool {
  font-size: 12px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #eff6ff;
  color: #1d4ed8;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.bubble.assistant .body.md {
  font-size: 14px;
  line-height: 1.55;
}
.bubble.assistant .body.md :deep(h3) {
  font-size: 14px;
  margin: 10px 0 6px;
}
.bubble.assistant .body.md :deep(code) {
  background: var(--el-fill-color);
  padding: 1px 4px;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.bubble.status {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}
@media (max-width: 900px) {
  .bottom-grid {
    grid-template-columns: 1fr;
  }
}
.check-row {
  margin-bottom: 4px;
}
.msg {
  margin-top: 10px;
  font-size: 13px;
  color: var(--el-color-success);
}
.msg.err {
  color: var(--el-color-danger);
}
.raw {
  margin-top: 10px;
  max-height: 220px;
  overflow: auto;
  background: #1c1917;
  color: #f5f5f4;
  border-radius: 8px;
  padding: 10px;
  font-size: 11px;
}
</style>
