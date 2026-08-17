export const PRODUCTION_LINES = ['SMT-1线', 'SMT-2线', 'DIP线', '组装线', '测试线']
export const WIP_STATUSES = ['待投料', '在制', '待检验', '待入库']

const LINE_PRODUCTS = {
  'SMT-1线': ['PCB-A100', 'PCB-A200', 'PCB-A300'],
  'SMT-2线': ['PCB-B100', 'PCB-B200', 'PCB-B300'],
  DIP线: ['PCBA-C100', 'PCBA-C200', 'PCBA-C300'],
  组装线: ['ASSY-D100', 'ASSY-D200', 'ASSY-D300'],
  测试线: ['TEST-E100', 'TEST-E200', 'TEST-E300'],
}

const LINE_DEVICES = {
  'SMT-1线': ['贴片机-01', '回流焊-01', 'AOI检测-01', '收板机-01'],
  'SMT-2线': ['贴片机-02', '回流焊-02', 'AOI检测-02', '收板机-02'],
  DIP线: ['插件机-01', '波峰焊-01', '剪脚机-01', 'ICT测试-01'],
  组装线: ['装配工位-01', '锁螺丝机-01', '点胶机-01', '包装机-01'],
  测试线: ['功能测试-01', '老化柜-01', '高压测试-01', '终检台-01'],
}

const DEFECT_TYPES = ['外观不良', '尺寸偏差', '虚焊', '元件偏移', '功能异常', '其他']

function seedOf(text) {
  let value = 0
  for (let i = 0; i < text.length; i += 1) {
    value = (value * 31 + text.charCodeAt(i)) >>> 0
  }
  return value
}

function lineIndex(line) {
  return line === '全部' ? 0 : PRODUCTION_LINES.indexOf(line)
}

function lineFactor(line) {
  if (line === '全部') return 1
  const idx = lineIndex(line)
  return idx >= 0 ? 0.96 + idx * 0.05 : 1
}

function trendLabelsAndPlan(period) {
  if (period === 'day') {
    return {
      labels: ['08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00'],
      plan: [1200, 1200, 1200, 1200, 1200, 900, 600],
    }
  }
  if (period === 'week') {
    return {
      labels: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      plan: [10000, 10000, 10000, 10000, 10000, 6000, 2000],
    }
  }
  return {
    labels: ['第1周', '第2周', '第3周', '第4周'],
    plan: [45000, 45000, 45000, 42000],
  }
}

function outputTrend(period, line) {
  const { labels, plan } = trendLabelsAndPlan(period)
  const factor = lineFactor(line)
  const seed = seedOf(line + period)
  const actual = plan.map((value, i) =>
    Math.round(value * factor * (0.93 + ((seed + i * 13) % 7) * 0.028)),
  )
  return {
    granularity: period === 'month' ? 'day' : period,
    labels,
    plan,
    actual,
  }
}

function achievementComparison(line) {
  if (line === '全部') {
    const plans = [12800, 11600, 9800, 9200, 10600]
    return PRODUCTION_LINES.map((name, idx) => {
      const planQuantity = plans[idx]
      const actualQuantity = Math.round(planQuantity * (0.9 + idx * 0.035))
      return {
        name,
        plan_quantity: planQuantity,
        actual_quantity: actualQuantity,
        achievement_rate: Number(((actualQuantity / planQuantity) * 100).toFixed(1)),
      }
    })
  }

  const products = LINE_PRODUCTS[line] || ['产品A', '产品B', '产品C']
  const basePlans = [5200, 4700, 4300]
  const seed = seedOf(line)
  return products.map((name, idx) => {
    const planQuantity = basePlans[idx]
    const actualQuantity = Math.round(
      planQuantity * (0.9 + ((seed + idx * 29) % 7) * 0.032),
    )
    return {
      name,
      plan_quantity: planQuantity,
      actual_quantity: actualQuantity,
      achievement_rate: Number(((actualQuantity / planQuantity) * 100).toFixed(1)),
    }
  })
}

function workOrderStatus(line) {
  const idx = lineIndex(line)
  const counts =
    line === '全部' ? [12, 18, 64] : [3, 4 + (idx % 3), 14 + idx * 2]
  return [
    { status: '待开工', count: counts[0] },
    { status: '进行中', count: counts[1] },
    { status: '完成', count: counts[2] },
  ]
}

function wipOverview(line) {
  if (line === '全部') {
    const base = [
      [120, 360, 210, 150],
      [95, 310, 180, 120],
      [80, 280, 160, 110],
      [110, 250, 170, 130],
      [70, 220, 140, 90],
    ]
    return {
      statuses: WIP_STATUSES,
      rows: PRODUCTION_LINES.map((name, i) => ({ name, values: base[i] })),
    }
  }

  const products = LINE_PRODUCTS[line] || ['产品A', '产品B', '产品C']
  const seed = seedOf(line + 'wip')
  return {
    statuses: WIP_STATUSES,
    rows: products.map((name, idx) => {
      const baseValues = [14 + idx * 6, 42 + idx * 9, 26 + idx * 5, 18 + idx * 4]
      const factor = 0.9 + ((seed + idx * 11) % 5) * 0.05
      return {
        name,
        values: baseValues.map((v) => Math.max(1, Math.round(v * factor))),
      }
    }),
  }
}

function lineLoad(line) {
  if (line === '全部') {
    const loads = [78, 86, 82, 74, 90]
    const caps = [84, 89, 80, 76, 93]
    return PRODUCTION_LINES.map((name, i) => ({
      name,
      load_rate: loads[i],
      capacity_utilization: caps[i],
    }))
  }

  const devices = LINE_DEVICES[line] || ['设备01', '设备02', '设备03', '设备04']
  const idx = lineIndex(line)
  return devices.map((name, i) => ({
    name,
    load_rate: Number((72 + idx * 2 + i * 5).toFixed(1)),
    capacity_utilization: Number((66 + idx * 3 + i * 6).toFixed(1)),
  }))
}

function quality(period, line) {
  const idx = lineIndex(line)
  const { labels } = trendLabelsAndPlan(period)
  const defectRate = line === '全部' ? 2.34 : Number((1.82 + idx * 0.38).toFixed(2))
  const seed = seedOf(line + period + 'defect')

  const defectRateTrend = labels.map((label, i) => ({
    label,
    value: Number(
      Math.max(0.4, defectRate + ((seed + i * 7) % 5 - 2) * 0.22).toFixed(2),
    ),
  }))

  const baseDistribution = [38, 26, 21, 17, 11, 6]
  const factor = line === '全部' ? 1 : 0.7 + idx * 0.08
  const defectDistribution = DEFECT_TYPES.map((name, i) => ({
    name,
    value: Math.max(1, Math.round(baseDistribution[i] * factor)),
  }))

  return {
    defect_rate: defectRate,
    defect_rate_trend: defectRateTrend,
    defect_distribution: defectDistribution,
  }
}

function equipment(line) {
  if (line === '全部') {
    return PRODUCTION_LINES.map((name, idx) => ({
      name,
      line_name: name,
      utilization: Number((76 + idx * 3.2).toFixed(1)),
      oee: Number((62 + idx * 2.4).toFixed(1)),
    }))
  }

  const devices = LINE_DEVICES[line] || ['设备01', '设备02', '设备03', '设备04']
  return devices.map((name, idx) => ({
    name,
    line_name: line,
    utilization: Number((70 + idx * 4).toFixed(1)),
    oee: Number((58 + idx * 3.2).toFixed(1)),
  }))
}

export function buildProductionOverviewMock({ period = 'day', line = '全部' } = {}) {
  const comparison = achievementComparison(line)
  const planQuantity = comparison.reduce((sum, item) => sum + item.plan_quantity, 0)
  const actualQuantity = comparison.reduce((sum, item) => sum + item.actual_quantity, 0)
  const achievementRate = planQuantity
    ? Number(((actualQuantity / planQuantity) * 100).toFixed(1))
    : 0

  const trend = outputTrend(period, line)
  const wip = wipOverview(line)
  const load = lineLoad(line)

  const planOutput = trend.plan.reduce((sum, value) => sum + value, 0)
  const actualOutput = trend.actual.reduce((sum, value) => sum + value, 0)
  const completionRate = planOutput
    ? Number(((actualOutput / planOutput) * 100).toFixed(1))
    : 0
  const wipTotal = wip.rows.reduce(
    (sum, row) => sum + row.values.reduce((a, b) => a + b, 0),
    0,
  )
  const avgLineLoad = load.length
    ? Number((load.reduce((sum, item) => sum + item.load_rate, 0) / load.length).toFixed(1))
    : 0

  const idx = lineIndex(line)
  const kpi =
    line === '全部'
      ? {
          today_output: 12860,
          week_output: 82640,
          in_progress_orders: 18,
          completed_orders: 236,
          pending_orders: 12,
        }
      : {
          today_output: Math.round(2680 * (1 + idx * 0.12)),
          week_output: Math.round(16800 * (1 + idx * 0.12)),
          in_progress_orders: 4 + idx,
          completed_orders: 52 + idx * 7,
          pending_orders: 3 + (idx % 3),
        }

  return {
    period,
    production_line: line,
    updated_at: new Date().toLocaleString('zh-CN', { hour12: false }),
    lines: PRODUCTION_LINES,
    kpi: {
      achievement_rate: achievementRate,
      plan_quantity: planQuantity,
      actual_quantity: actualQuantity,
      achievement_diff: actualQuantity - planQuantity,
      ...kpi,
      completion_rate: completionRate,
      completion_rate_trend: '+2.1%',
      wip_total: wipTotal,
      wip_total_trend: '+3.4%',
      avg_line_load: avgLineLoad,
      avg_line_load_trend: '-1.2%',
      plan_achievement_rate: achievementRate,
      plan_achievement_rate_trend: '+1.6%',
    },
    achievement_comparison: comparison,
    output_trend: trend,
    work_order_status: workOrderStatus(line),
    line_load: load,
    wip_overview: wip,
    quality: quality(period, line),
    equipment: equipment(line),
  }
}
