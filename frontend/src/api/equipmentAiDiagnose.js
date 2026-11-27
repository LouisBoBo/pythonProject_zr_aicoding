/** AI 诊断中转服务（勿直连 Dify） */

const DEFAULT_TIMEOUT_MS = 90000

function getAiDiagnoseBase() {
  const raw = import.meta.env.VITE_AI_DIAGNOSE_BASE
  if (typeof raw === 'string' && raw.trim()) {
    return raw.trim().replace(/\/$/, '')
  }
  // 本地默认走 Vite 代理 /ai-api → 诊断服务 :8000，避免跨域
  return '/ai-api'
}

/**
 * 调用中转服务做设备故障 AI 诊断
 * @param {{ repairId?: number, equipmentCode: string, equipmentName?: string, faultDesc: string, user?: string }} payload
 * @param {{ timeoutMs?: number }} [options]
 * @returns {Promise<{ code: number, message: string, data: { diagnosis: string, conversationId?: string, messageId?: string, repairId?: number } | null }>}
 */
export async function requestAiDiagnose(payload, options = {}) {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const base = getAiDiagnoseBase()
  const url = `${base}/api/equipment/ai-diagnose`
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        repairId: payload.repairId,
        equipmentCode: payload.equipmentCode,
        equipmentName: payload.equipmentName,
        faultDesc: payload.faultDesc,
        user: payload.user,
      }),
      signal: controller.signal,
    })

    const data = await response.json().catch(() => null)
    if (data && typeof data.code === 'number') {
      return data
    }

    if (!response.ok) {
      return {
        code: 1,
        message: '诊断服务暂不可用',
        data: null,
      }
    }

    return {
      code: 1,
      message: '诊断服务暂不可用',
      data: null,
    }
  } catch (err) {
    if (err?.name === 'AbortError') {
      return { code: 1, message: '诊断服务暂不可用', data: null }
    }
    return { code: 1, message: '诊断服务暂不可用', data: null }
  } finally {
    clearTimeout(timer)
  }
}
