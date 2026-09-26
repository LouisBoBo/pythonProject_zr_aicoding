/** ERP 能力问答应与 WorkBuddy 插件状态一致（含 mes_ask / 四类能力） */
async function login() {
  const res = await fetch('http://127.0.0.1:5175/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: 'admin',
      password: 'admin123',
      enterprise_code: '测试企业',
    }),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(JSON.stringify(data))
  return data.access_token
}

async function erpReply(token, message) {
  const res = await fetch('http://127.0.0.1:5175/api/workbuddy/chat/stream', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
  })
  const text = await res.text()
  let reply = ''
  for (const block of text.split('\n\n')) {
    for (const line of block.split('\n')) {
      if (!line.startsWith('data:')) continue
      const evt = JSON.parse(line.slice(5).trim())
      if (evt.type === 'done') reply = evt.reply || reply
    }
  }
  return reply
}

async function wbChat(message) {
  const res = await fetch('http://127.0.0.1:18000/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  const text = await res.text()
  let reply = ''
  for (const block of text.split('\n\n')) {
    for (const line of block.split('\n')) {
      if (!line.startsWith('data:')) continue
      const evt = JSON.parse(line.slice(5).trim())
      if (evt.type === 'done') reply = evt.reply || reply
    }
  }
  return reply
}

const token = await login()
const msg = '你有什么功能'
const erp = await erpReply(token, msg)
const wb = await wbChat(msg)

const checks = {
  erpHasMesAsk: erp.includes('mes_ask'),
  erpHasFourSections: erp.includes('## 1.') && erp.includes('## 4.'),
  erpRicherThanPlainChat: erp.length > wb.length + 200,
  erpLen: erp.length,
  wbLen: wb.length,
}
checks.ok = checks.erpHasMesAsk && checks.erpHasFourSections && checks.erpRicherThanPlainChat
console.log(JSON.stringify(checks, null, 2))
process.exit(checks.ok ? 0 : 1)
