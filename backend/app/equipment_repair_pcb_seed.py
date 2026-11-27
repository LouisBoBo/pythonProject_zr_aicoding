"""PCB 产线设备维修工单演示数据（幂等）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import Equipment, EquipmentRepair

# 故障描述与用户提供的 16 条原文一致（含两条「压辊寿命到期需更换」）
PCB_REPAIR_FAULT_ROWS: list[dict] = [
    {"no_suffix": "0001", "fault_description": "烤炉超温", "fault_category": "机械故障", "urgency": "high"},
    {"no_suffix": "0002", "fault_description": "微蚀缸过滤无压力", "fault_category": "液压故障", "urgency": "normal"},
    {"no_suffix": "0003", "fault_description": "化铜缸气管漏气", "fault_category": "气动故障", "urgency": "high"},
    {"no_suffix": "0004", "fault_description": "主轴温度报警", "fault_category": "机械故障", "urgency": "high"},
    {"no_suffix": "0005", "fault_description": "主轴压刀", "fault_category": "机械故障", "urgency": "normal"},
    {"no_suffix": "0006", "fault_description": "砂轮马达异常", "fault_category": "电气故障", "urgency": "normal"},
    {"no_suffix": "0007", "fault_description": "B平台出料异常", "fault_category": "机械故障", "urgency": "normal"},
    {"no_suffix": "0008", "fault_description": "4A没扭力，换主轴", "fault_category": "机械故障", "urgency": "high"},
    {"no_suffix": "0009", "fault_description": "上移栽α吸盘伸张气缸异常", "fault_category": "气动故障", "urgency": "normal"},
    {"no_suffix": "0010", "fault_description": "入料口滚轮异响", "fault_category": "传动故障", "urgency": "normal"},
    {"no_suffix": "0011", "fault_description": "设备断电", "fault_category": "电气故障", "urgency": "urgent"},
    {"no_suffix": "0012", "fault_description": "送料皮带打滑，放不准", "fault_category": "传动故障", "urgency": "normal"},
    {"no_suffix": "0013", "fault_description": "压辊寿命到期需更换", "fault_category": "机械故障", "urgency": "normal"},
    {"no_suffix": "0014", "fault_description": "压辊寿命到期需更换", "fault_category": "机械故障", "urgency": "normal"},
    {"no_suffix": "0015", "fault_description": "没有吸尘", "fault_category": "其他", "urgency": "normal"},
    {"no_suffix": "0016", "fault_description": "中和缸 整孔缸超温", "fault_category": "其他", "urgency": "high"},
]

_REPAIR_NO_PREFIX = "RE-PCB-DEMO-"
_REPORTERS = ("张三", "李四", "王五", "赵六", "操作员")


def ensure_pcb_equipment_repair_orders() -> None:
    """补齐 PCB 产线 16 条维修工单；按固定工单号幂等，可重复启动。"""
    db = SessionLocal()
    try:
        marker = f"{_REPAIR_NO_PREFIX}0001"
        if db.query(EquipmentRepair).filter(EquipmentRepair.repair_no == marker).first():
            return

        equipment_list = db.query(Equipment).order_by(Equipment.id).all()
        if not equipment_list:
            return

        now = datetime.utcnow()
        rows: list[EquipmentRepair] = []
        for idx, spec in enumerate(PCB_REPAIR_FAULT_ROWS):
            eq = equipment_list[idx % len(equipment_list)]
            created = now - timedelta(hours=len(PCB_REPAIR_FAULT_ROWS) - idx)
            rows.append(
                EquipmentRepair(
                    repair_no=f"{_REPAIR_NO_PREFIX}{spec['no_suffix']}",
                    equipment_id=eq.id,
                    fault_category=spec["fault_category"],
                    fault_description=spec["fault_description"],
                    urgency=spec["urgency"],
                    status="pending",
                    reporter=_REPORTERS[idx % len(_REPORTERS)],
                    repair_person=None,
                    start_time=None,
                    repair_completed_at=None,
                    repair_description=None,
                    images=[],
                    created_at=created,
                    updated_at=created,
                )
            )
        db.add_all(rows)
        db.commit()
    finally:
        db.close()