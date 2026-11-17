import { normalizeAssistantText } from './markdownLite.js'

/** 兼容上游「增量 delta」与「累积全文 delta」，只取尚未展示的后缀 */
export function takeStreamIncrement(accum, incoming) {
  const base = normalizeAssistantText(accum)
  const next = normalizeAssistantText(incoming)
  if (!next) return { accum: base, increment: '' }
  if (next === base) return { accum: base, increment: '' }
  if (next.startsWith(base)) {
    return { accum: next, increment: next.slice(base.length) }
  }
  if (base.startsWith(next)) {
    return { accum: base, increment: '' }
  }
  if (base.endsWith(next)) {
    return { accum: base, increment: '' }
  }
  if (next.length >= 16 && base.includes(next)) {
    return { accum: base, increment: '' }
  }
  const maxOverlap = Math.min(base.length, next.length)
  for (let i = maxOverlap; i > 0; i--) {
    if (base.endsWith(next.slice(0, i))) {
      const merged = base + next.slice(i)
      return { accum: merged, increment: next.slice(i) }
    }
  }
  let common = 0
  const cap = Math.min(base.length, next.length)
  while (common < cap && base[common] === next[common]) common += 1
  if (common >= 12 && next.length > common) {
    return { accum: next, increment: next.slice(common) }
  }
  // 上游偶发再发一篇完整新稿（开头不同），应替换而非拼接
  if (base.length >= 160 && next.length >= 160) {
    const ratio = common / Math.min(base.length, next.length)
    if (ratio < 0.12) {
      return { accum: next, increment: next, replace: true }
    }
  }
  return { accum: base + next, increment: next }
}

/**
 * 网络层可成批到达；用 rAF 逐段追赶 canonical，不阻塞 SSE 读取。
 */
export function attachSmoothDisplay(assistant, field, { charsPerFrame = 14, onFrame } = {}) {
  let target = ''
  let rafId = 0

  function pump() {
    rafId = 0
    const cur = assistant[field] || ''
    if (cur.length >= target.length) {
      if (cur !== target) assistant[field] = target
      onFrame?.()
      return
    }
    const nextLen = Math.min(target.length, cur.length + charsPerFrame)
    assistant[field] = target.slice(0, nextLen)
    onFrame?.()
    rafId = globalThis.requestAnimationFrame(pump)
  }

  function schedule() {
    if (!rafId) rafId = globalThis.requestAnimationFrame(pump)
  }

  return {
    setTarget(text) {
      target = normalizeAssistantText(text)
      schedule()
    },
    flush() {
      if (rafId) globalThis.cancelAnimationFrame(rafId)
      rafId = 0
      target = normalizeAssistantText(target)
      assistant[field] = target
      onFrame?.()
    },
  }
}

/** 保证用户可见的逐段输出（SSE 常一次到达整段 delta） */
export function createTextReveal(appendFn, { charsPerStep = 3, stepMs = 16 } = {}) {
  let receivedLen = 0
  let chain = Promise.resolve()
  let generation = 0

  function animate(text) {
    const normalized = normalizeAssistantText(text)
    if (!normalized) return Promise.resolve()
    const gen = generation
    receivedLen += normalized.length
    return new Promise((resolve) => {
      let offset = 0
      const tick = () => {
        if (gen !== generation) {
          resolve()
          return
        }
        if (offset >= normalized.length) {
          resolve()
          return
        }
        const piece = normalized.slice(offset, offset + charsPerStep)
        offset += charsPerStep
        appendFn(piece)
        globalThis.setTimeout(tick, stepMs)
      }
      tick()
    })
  }

  return {
    get receivedLength() {
      return receivedLen
    },
    enqueue(text) {
      chain = chain.then(() => animate(text))
      return chain
    },
    finished() {
      return chain
    },
    /** done 事件用权威全文覆盖，避免流式合并误差 */
    syncCanonical(text) {
      const normalized = normalizeAssistantText(text)
      generation += 1
      chain = Promise.resolve()
      receivedLen = normalized.length
    },
  }
}
