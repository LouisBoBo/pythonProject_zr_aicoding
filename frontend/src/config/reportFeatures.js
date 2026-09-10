/**
 * 报表功能注册表（唯一配置入口）。
 * - menu: false → 侧栏隐藏（删菜单只改这里，勿删 api/视图文件）
 * - hub: false → 报表中心首页不展示入口
 * - enabled: false → 强制下线（即使文件还在）
 * 路由/菜单仅注册「enabled + 视图文件存在 + api 文件存在（若声明）」的项，缺文件不会拖垮整站。
 */
export const REPORT_CATALOG = [
  {
    id: 'wip',
    routePath: 'wip',
    viewFile: 'WipReportView.vue',
    apiFile: 'wip.js',
    title: '在制品报表',
    description: '按工单查看工序与在制数量（wip 口径）',
    icon: 'Document',
    menu: true,
    hub: true,
    enabled: true,
  },
  {
    id: 'daily-output',
    routePath: 'daily-output',
    viewFile: 'DailyOutputReportView.vue',
    apiFile: 'dailyOutput.js',
    title: '日产报表',
    description: '按日 / 产线 / 产品查看计划与实际产量',
    icon: 'DataAnalysis',
    menu: true,
    hub: true,
    enabled: true,
  },
  {
    id: 'equipment',
    routePath: 'equipment',
    viewFile: 'EquipmentReportView.vue',
    apiFile: null,
    title: '设备管理',
    description: '设备档案台账查询，按编号/名称/部门/状态筛选',
    icon: 'Cpu',
    menu: false,
    hub: true,
    enabled: true,
  },
  {
    id: 'equipment-repairs',
    routePath: 'equipment-repairs',
    viewFile: 'EquipmentRepairReportView.vue',
    apiFile: 'equipmentRepair.js',
    title: '设备维修',
    description: '维修工单查询、详情查看与 Excel 导出',
    icon: 'Tools',
    menu: false,
    hub: true,
    enabled: true,
  },
  {
    id: 'employee-work-hours',
    routePath: 'employee-work-hours',
    viewFile: 'EmployeeWorkHoursReportView.vue',
    apiFile: 'employeeWorkHours.js',
    title: '员工工时',
    description: '按员工/项目/部门统计工时，支持多维度汇总与 Excel 导出',
    icon: 'Timer',
    menu: false,
    hub: true,
    enabled: true,
  },
]
