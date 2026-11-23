/**
 * PCB 产线设备维修工单演示数据（与后端 RE-PCB-DEMO-* 种子一致，供维修管理页展示/筛选）。
 */
export const PCB_REPAIR_NO_PREFIX = 'RE-PCB-DEMO-'

/** @type {ReadonlyArray<{ noSuffix: string, faultDescription: string }>} */
export const PCB_EQUIPMENT_REPAIR_ORDERS = Object.freeze([
  { noSuffix: '0001', faultDescription: '烤炉超温' },
  { noSuffix: '0002', faultDescription: '微蚀缸过滤无压力' },
  { noSuffix: '0003', faultDescription: '化铜缸气管漏气' },
  { noSuffix: '0004', faultDescription: '主轴温度报警' },
  { noSuffix: '0005', faultDescription: '主轴压刀' },
  { noSuffix: '0006', faultDescription: '砂轮马达异常' },
  { noSuffix: '0007', faultDescription: 'B平台出料异常' },
  { noSuffix: '0008', faultDescription: '4A没扭力，换主轴' },
  { noSuffix: '0009', faultDescription: '上移栽α吸盘伸张气缸异常' },
  { noSuffix: '0010', faultDescription: '入料口滚轮异响' },
  { noSuffix: '0011', faultDescription: '设备断电' },
  { noSuffix: '0012', faultDescription: '送料皮带打滑，放不准' },
  { noSuffix: '0013', faultDescription: '压辊寿命到期需更换' },
  { noSuffix: '0014', faultDescription: '压辊寿命到期需更换' },
  { noSuffix: '0015', faultDescription: '没有吸尘' },
  { noSuffix: '0016', faultDescription: '中和缸 整孔缸超温' },
])

export function pcbRepairOrderNo(noSuffix) {
  return `${PCB_REPAIR_NO_PREFIX}${noSuffix}`
}

export function isPcbDemoRepairNo(repairNo) {
  return typeof repairNo === 'string' && repairNo.startsWith(PCB_REPAIR_NO_PREFIX)
}