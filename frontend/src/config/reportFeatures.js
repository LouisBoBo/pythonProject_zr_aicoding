// workbuddy-e2e-pipeline-verify-20260925
// mes-dev-pipeline-tooling-verify-20260926
// cch-20261008-report-center-remove-pcb-production-ops-menu
// cch-20261008-report-center-add-daily-output-menu
// cch-20261008-daily-output-add-device-column
// cch-20261008-daily-output-device-explicit-association-only
// cch-20261008-daily-output-add-order-no-column
// cch-20261008-daily-output-null-line-id-guard
// cch-20261009-report-center-add-employee-work-hours-menu
/**
 * 报表功能注册表（唯一配置入口）。
 * 开发流水线偏好见 mesDevPipelinePreferences.js；侧栏「报表中心」菜单由此表驱动。
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
    // 列表在「计划产量」与「实际产量」之间展示「订单号」，数据来自 /api/reports/daily-output 的 order_no
    description:
      '按日 / 车间 / 产线查看计划产量、订单号、实际产量、达成率、不良与工时、生产人员',
    icon: 'DataAnalysis',
    menu: true,
    hub: true,
    enabled: true,
  },
  {
    id: 'employee-work-hours',
    routePath: 'employee-work-hours',
    viewFile: 'EmployeeWorkHoursReportView.vue',
    apiFile: 'employeeWorkHours.js',
    title: '员工工时报表',
    description: '按日期区间与部门查询员工工时明细，支持按员工汇总工时合计',
    icon: 'Timer',
    menu: true,
    hub: true,
    enabled: true,
  },
  {
    id: 'pcb-production-ops',
    routePath: 'pcb-production-ops',
    viewFile: 'PcbProductionOpsReportView.vue',
    apiFile: 'pcbProductionOps.js',
    title: 'PCB 生产运营分析',
    description:
      'MES 连通与近 7 日产出/工单趋势、在制与异常核查；仅实际量与工时，作废口径列为盲区',
    icon: 'TrendCharts',
    menu: false,
    hub: false,
    enabled: true,
  },
  {
    id: 'equipment-downtime',
    routePath: 'equipment-downtime',
    viewFile: 'EquipmentDowntimeReportView.vue',
    apiFile: 'equipmentDowntime.js',
    title: '停机报表',
    description: '按时间、车间与设备查询停机/维修/待机明细，含趋势、维度统计与 MTBF/MTTR，支持 Excel 导出',
    icon: 'Odometer',
    menuGroup: 'equipment',
    menu: false,
    hub: false,
    enabled: false,
  },
  {
    id: 'equipment-repairs',
    routePath: 'equipment-repairs',
    viewFile: 'EquipmentRepairReportView.vue',
    apiFile: 'equipmentRepair.js',
    title: '设备维修报表',
    description: '维修工单明细：设备、故障时间、故障现象、维修人、耗时与状态',
    icon: 'Tools',
    menu: false,
    hub: false,
    enabled: true,
  },
  {
    id: 'equipment-inspection',
    routePath: 'equipment-inspection',
    viewFile: 'EquipmentInspectionReportView.vue',
    apiFile: 'equipmentInspection.js',
    title: '设备点检报表',
    description: '按设备与时间查询点检明细，含点检项、结果、点检人与点检时间',
    icon: 'List',
    menu: false,
    hub: false,
    enabled: true,
  },
  {
    id: 'equipment-maintenance',
    routePath: 'equipment-maintenance',
    viewFile: 'EquipmentMaintenanceReportView.vue',
    apiFile: 'equipmentMaintenanceReport.js',
    title: '设备保养报表',
    description: '保养计划执行情况与保养记录明细，支持条件查询与 Excel 导出',
    icon: 'Calendar',
    menu: false,
    hub: false,
    enabled: true,
  },
]
