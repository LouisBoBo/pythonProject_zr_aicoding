/** SSE 到达后按小步写入 UI，避免整段弹出（上游常一次返回整段 delta） */
export function createIncrementalAppender(appendFn, { charsPerTick = 6, tickMs = 12 } = {}) {
  let queue = ''
  let timer = null
  let flushWaiter = null
  let totalPushed = 0

  function finishFlushIfIdle() {
    if (queue.length || timer) return
    if (flushWaiter) {
      const done = flushWaiter
      flushWaiter = null
      done()
    }
  }

  function tick() {
    timer = null
    if (!queue.length) {
      finishFlushIfIdle()
      return
    }
    const piece = queue.slice(0, charsPerTick)
    queue = queue.slice(charsPerTick)
    appendFn(piece)
    timer = globalThis.setTimeout(tick, tickMs)
  }

  function schedule() {
    if (!timer) timer = globalThis.setTimeout(tick, tickMs)
  }

  return {
    get receivedLength() {
      return totalPushed
    },
    push(text) {
      if (!text) return
      totalPushed += text.length
      queue += text
      schedule()
    },
    flush() {
      if (!queue.length && !timer) return Promise.resolve()
      return new Promise((resolve) => {
        flushWaiter = resolve
        if (!timer) tick()
      })
    },
  }
}
