import { Calendar, Cpu, DataAnalysis, DataLine, Document, List, Odometer, Timer, Tools, User } from '@element-plus/icons-vue'

export const REPORT_ICON_MAP = {
  Document,
  DataAnalysis,
  Cpu,
  Tools,
  Odometer,
  List,
  Calendar,
  Timer,
  User,
}

/** 报表注册表 icon 名 → 组件；fallback 默认 DataLine */
export function resolveReportIcon(name, fallback = DataLine) {
  return REPORT_ICON_MAP[name] || fallback
}
