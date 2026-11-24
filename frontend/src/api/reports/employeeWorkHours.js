/**
 * 员工工时报表 API（当前为本地演示数据；后端接口待接入）
 *
 * TODO: 接入 GET /api/reports/employee-work-hours
 * TODO: 接入 GET /api/reports/employee-work-hours/filters
 * TODO: 接入 GET /api/reports/employee-work-hours/export
 */

const DEMO_EMPLOYEES = [
  { employee_no: 'E1001', name: '张三', department: '生产一部' },
  { employee_no: 'E1002', name: '李四', department: '生产一部' },
  { employee_no: 'E1003', name: '王五', department: '生产二部' },
  { employee_no: 'E1004', name: '赵六', department: '品质部' },
  { employee_no: 'E1005', name: '钱七', department: '设备部' },
  { employee_no: 'E1006', name: '孙八', department: '仓储部' },
]

function pad2(n) {
  return String(n).padStart(2, '0')
}

function formatDate(d) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

function addDays(base, delta) {
  const d = new Date(base)
  d.setDate(d.getDate() + delta)
  return d
}

/** 演示明细：近 21 天内每位员工若干出勤记录 */
function buildDemoRows() {
  const end = new Date()
  const rows = []
  let seed = 0
  for (const emp of DEMO_EMPLOYEES) {
    for (let dayOffset = 0; dayOffset < 21; dayOffset += 1) {
      const d = addDays(end, -dayOffset)
      const dow = d.getDay()
      if (dow === 0 || dow === 6) continue
      seed += 1
      const attendance = 7.5 + (seed % 4) * 0.5
      const overtime = seed % 5 === 0 ? 1.5 + (seed % 3) * 0.5 : seed % 7 === 0 ? 2 : 0
      const total = Math.round((attendance + overtime) * 10) / 10
      rows.push({
        work_date: formatDate(d),
        employee_no: emp.employee_no,
        employee_name: emp.name,
        department: emp.department,
        attendance_hours: attendance,
        overtime_hours: overtime,
        total_hours: total,
      })
    }
  }
  return rows.sort((a, b) => b.work_date.localeCompare(a.work_date) || a.employee_no.localeCompare(b.employee_no))
}

const DEMO_ROWS = buildDemoRows()

function delay(ms = 120) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

function withinDateRange(workDate, dateFrom, dateTo) {
  if (dateFrom && workDate < dateFrom) return false
  if (dateTo && workDate > dateTo) return false
  return true
}

function filterRows({ dateFrom, dateTo, employeeNo, department, keyword }) {
  const kw = (keyword || '').trim().toLowerCase()
  return DEMO_ROWS.filter((row) => {
    if (!withinDateRange(row.work_date, dateFrom, dateTo)) return false
    if (employeeNo && row.employee_no !== employeeNo) return false
    if (department && row.department !== department) return false
    if (kw) {
      const hay = `${row.employee_no}${row.employee_name}${row.department}`.toLowerCase()
      if (!hay.includes(kw)) return false
    }
    return true
  })
}

function sumHours(rows) {
  let attendance = 0
  let overtime = 0
  let total = 0
  for (const row of rows) {
    attendance += Number(row.attendance_hours) || 0
    overtime += Number(row.overtime_hours) || 0
    total += Number(row.total_hours) || 0
  }
  return {
    attendance_hours_sum: Math.round(attendance * 10) / 10,
    overtime_hours_sum: Math.round(overtime * 10) / 10,
    total_hours_sum: Math.round(total * 10) / 10,
  }
}

export async function fetchEmployeeWorkHoursFilters() {
  await delay()
  // TODO: return authFetch('/api/reports/employee-work-hours/filters')
  const departments = [...new Set(DEMO_EMPLOYEES.map((e) => e.department))].sort()
  return {
    employees: DEMO_EMPLOYEES.map((e) => ({
      employee_no: e.employee_no,
      name: e.name,
      label: `${e.employee_no} · ${e.name}`,
    })),
    departments,
  }
}

export async function fetchEmployeeWorkHoursReport({
  page = 1,
  pageSize = 10,
  dateFrom,
  dateTo,
  employeeNo,
  department,
  keyword,
} = {}) {
  await delay()
  // TODO: authFetch with query params
  const filtered = filterRows({ dateFrom, dateTo, employeeNo, department, keyword })
  const sums = sumHours(filtered)
  const start = (page - 1) * pageSize
  const items = filtered.slice(start, start + pageSize)
  return {
    items,
    total: filtered.length,
    ...sums,
    _demo: true,
  }
}

/** 演示导出：按当前筛选条件导出全部明细为 CSV（后端就绪后改走 export 接口） */
export async function exportEmployeeWorkHoursDemoCsv({
  dateFrom,
  dateTo,
  employeeNo,
  department,
  keyword,
} = {}) {
  await delay(80)
  const rows = filterRows({ dateFrom, dateTo, employeeNo, department, keyword })
  const header = ['日期', '工号', '姓名', '部门', '出勤工时', '加班工时', '合计']
  const escape = (v) => {
    const s = String(v ?? '')
    if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`
    return s
  }
  const lines = [header.join(',')]
  for (const row of rows) {
    lines.push(
      [
        row.work_date,
        row.employee_no,
        row.employee_name,
        row.department,
        row.attendance_hours,
        row.overtime_hours,
        row.total_hours,
      ]
        .map(escape)
        .join(',')
    )
  }
  const sums = sumHours(rows)
  lines.push(
    ['合计', '', '', '', sums.attendance_hours_sum, sums.overtime_hours_sum, sums.total_hours_sum]
      .map(escape)
      .join(',')
  )
  const blob = new Blob([`\ufeff${lines.join('\n')}`], { type: 'text/csv;charset=utf-8' })
  return { blob, rowCount: rows.length }
}