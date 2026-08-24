from contextlib import asynccontextmanager

from datetime import date, datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from sqlalchemy import inspect, text
from sqlalchemy.orm import joinedload

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.openapi_zh import OPENAPI_TAGS, apply_chinese_openapi
from app.models import (
    Device,
    DeviceType,
    Equipment,
    EquipmentMaintenanceOrder,
    EquipmentMaintenancePlan,
    EquipmentRepair,
    EquipmentRepairPart,
    InspectionPlan,
    InspectionPlanItem,
    InspectionRecord,
    InspectionRecordItem,
    InventoryBalance,
    InventoryStock,
    InventoryTransaction,
    Material,
    MaterialInbound,
    QualityAnomaly,
    QualityDefectDetail,
    QualityMetrics,
    User,
    Warehouse,
    WarehouseLocation,
)
from app.routers import (
    auth,
    dashboard,
    device_dashboard,
    devices,
    equipment,
    equipment_maintenance,
    equipment_repair,
    inspection,
    kanban_boards,
    kanban_general,
    kanban_production,
    production,
    quality,
    reports,
    warehouse,
    work_orders,
)
from app.seed_analytics import backfill_recent_operational_data, seed_analytics_data


def seed_default_user():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            db.add(
                User(
                    username="admin",
                    hashed_password=hash_password("admin123"),
                    role="admin",
                )
            )
            db.commit()
    finally:
        db.close()


def ensure_work_orders_actual_start_time():
    """为已有数据库的 work_orders 表补齐 actual_start_time 列，并回填已开工/已完成且为空的演示数据。"""
    inspector = inspect(engine)
    columns = [column["name"] for column in inspector.get_columns("work_orders")]
    if "actual_start_time" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE work_orders ADD COLUMN actual_start_time DATETIME"))
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE work_orders
                SET actual_start_time = datetime(start_date || ' 08:00:00')
                WHERE actual_start_time IS NULL
                  AND start_date IS NOT NULL
                  AND status IN ('in_progress', 'completed', 'closed')
                """
            )
        )


def ensure_maintenance_orders_plan_complete_date():
    """为已有数据库的 equipment_maintenance_orders 表补齐 plan_complete_date 列，并回填已开工/已完成存量工单。"""
    inspector = inspect(engine)
    if not inspector.has_table("equipment_maintenance_orders"):
        return
    columns = [column["name"] for column in inspector.get_columns("equipment_maintenance_orders")]
    if "plan_complete_date" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE equipment_maintenance_orders ADD COLUMN plan_complete_date DATE")
            )
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE equipment_maintenance_orders
                SET plan_complete_date = (
                    SELECT date(next_due_at)
                    FROM equipment_maintenance_plans
                    WHERE equipment_maintenance_plans.id = equipment_maintenance_orders.plan_id
                )
                WHERE plan_complete_date IS NULL
                  AND plan_id IS NOT NULL
                  AND status IN ('in_progress', 'completed')
                """
            )
        )


def ensure_work_orders_actual_end_time():
    """为已有数据库的 work_orders 表补齐 actual_end_time 列，并回填已完成/已关闭且为空的演示数据。"""
    inspector = inspect(engine)
    columns = [column["name"] for column in inspector.get_columns("work_orders")]
    if "actual_end_time" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE work_orders ADD COLUMN actual_end_time DATETIME"))
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE work_orders
                SET actual_end_time = datetime(end_date || ' 18:00:00')
                WHERE actual_end_time IS NULL
                  AND end_date IS NOT NULL
                  AND status IN ('completed', 'closed')
                """
            )
        )


def ensure_work_orders_current_process():
    """为 work_orders 补齐 current_process 列，并按进度回填已开工/已完成工单工序。"""
    from app.models import WorkOrder
    from app.work_order_utils import derive_current_process

    inspector = inspect(engine)
    columns = [column["name"] for column in inspector.get_columns("work_orders")]
    if "current_process" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE work_orders ADD COLUMN current_process VARCHAR(50)"))

    db = SessionLocal()
    try:
        orders = db.query(WorkOrder).all()
        changed = 0
        for wo in orders:
            expected = derive_current_process(wo.status, wo.plan_quantity, wo.actual_quantity)
            if wo.current_process != expected:
                wo.current_process = expected
                changed += 1
        if changed:
            db.commit()
    finally:
        db.close()


def ensure_equipment_repairs_repair_completed_at():
    """为已有数据库的 equipment_repairs 表补齐 repair_completed_at 列，并回填已完成/已关闭存量工单。"""
    inspector = inspect(engine)
    if not inspector.has_table("equipment_repairs"):
        return
    columns = [column["name"] for column in inspector.get_columns("equipment_repairs")]
    if "repair_completed_at" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE equipment_repairs ADD COLUMN repair_completed_at DATETIME")
            )
        columns.append("repair_completed_at")
    if "completion_time" in columns:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE equipment_repairs
                    SET repair_completed_at = completion_time
                    WHERE repair_completed_at IS NULL
                      AND completion_time IS NOT NULL
                    """
                )
            )
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE equipment_repairs
                SET repair_completed_at = updated_at
                WHERE repair_completed_at IS NULL
                  AND status IN ('completed', 'closed')
                """
            )
        )


def ensure_inventory_stock_backfill():
    """从 inventory_balances 聚合回填 inventory_stock（表为空时执行，保证列表有演示数据）。"""
    inspector = inspect(engine)
    if not inspector.has_table("inventory_stock"):
        return
    if not inspector.has_table("inventory_balances"):
        return

    db = SessionLocal()
    try:
        if db.query(InventoryStock).count() > 0:
            return

        default_wh = db.query(Warehouse).order_by(Warehouse.id).first()
        if not default_wh:
            return

        materials = {m.id: m for m in db.query(Material).all()}
        loc_wh_map = {
            loc.id: loc.warehouse_id for loc in db.query(WarehouseLocation).all()
        }
        wh_names = {w.id: w.name for w in db.query(Warehouse).all()}

        agg: dict[tuple[int, int], dict] = {}
        for bal in db.query(InventoryBalance).all():
            wh_id = loc_wh_map.get(bal.location_id) if bal.location_id else default_wh.id
            if not wh_id:
                wh_id = default_wh.id
            key = (bal.material_id, wh_id)
            if key not in agg:
                agg[key] = {"quantity": 0, "updated_at": bal.updated_at}
            agg[key]["quantity"] += bal.quantity
            if bal.updated_at > agg[key]["updated_at"]:
                agg[key]["updated_at"] = bal.updated_at

        for (material_id, warehouse_id), data in agg.items():
            material = materials.get(material_id)
            if not material:
                continue
            db.add(
                InventoryStock(
                    material_id=material_id,
                    material_code=material.material_code,
                    material_name=material.material_name,
                    warehouse_id=warehouse_id,
                    warehouse_name=wh_names.get(warehouse_id, default_wh.name),
                    quantity=data["quantity"],
                    unit=material.unit,
                    safety_stock=material.safety_stock,
                    updated_at=data["updated_at"],
                )
            )
        db.commit()
    finally:
        db.close()


def ensure_material_inbound_backfill():
    """从 inventory_transactions 入库流水回填 material_inbounds（表为空时执行）。"""
    inspector = inspect(engine)
    if not inspector.has_table("material_inbounds"):
        return
    if not inspector.has_table("inventory_transactions"):
        return

    db = SessionLocal()
    try:
        if db.query(MaterialInbound).count() > 0:
            return

        txns = (
            db.query(InventoryTransaction)
            .options(joinedload(InventoryTransaction.material))
            .filter(InventoryTransaction.txn_type == "in")
            .order_by(InventoryTransaction.txn_at.asc())
            .all()
        )
        if not txns:
            return

        wh_map = {w.id: w for w in db.query(Warehouse).all()}
        loc_map = {loc.id: loc for loc in db.query(WarehouseLocation).all()}
        default_wh = db.query(Warehouse).order_by(Warehouse.id).first()
        handlers = ["张三", "李四", "王五", "赵六"]

        for idx, txn in enumerate(txns):
            material = txn.material
            if not material:
                continue
            loc = loc_map.get(txn.location_id) if txn.location_id else None
            wh_id = loc.warehouse_id if loc else (default_wh.id if default_wh else None)
            if not wh_id:
                continue
            wh = wh_map.get(wh_id)
            if not wh:
                continue

            inbound_no = txn.ref_no or f"RK-{txn.txn_at:%Y%m%d}-{idx + 1:03d}"
            if db.query(MaterialInbound).filter(MaterialInbound.inbound_no == inbound_no).first():
                inbound_no = f"{inbound_no}-{idx + 1}"

            db.add(
                MaterialInbound(
                    inbound_no=inbound_no,
                    material_id=material.id,
                    material_code=material.material_code,
                    material_name=material.material_name,
                    spec=material.spec,
                    quantity=txn.quantity,
                    unit=material.unit,
                    warehouse_id=wh.id,
                    warehouse_name=wh.name,
                    location_id=txn.location_id,
                    location_code=loc.location_code if loc else None,
                    inbound_date=txn.txn_at.date(),
                    handler=handlers[idx % len(handlers)],
                    status="completed",
                    created_at=txn.txn_at,
                )
            )

        # 追加 1 条待入库演示数据
        first_material = db.query(Material).order_by(Material.id).first()
        first_wh = default_wh
        first_loc = (
            db.query(WarehouseLocation)
            .filter(WarehouseLocation.warehouse_id == first_wh.id, WarehouseLocation.status == "free")
            .first()
            if first_wh
            else None
        )
        if first_material and first_wh:
            pending_no = f"RK-{date.today():%Y%m%d}-P01"
            if not db.query(MaterialInbound).filter(MaterialInbound.inbound_no == pending_no).first():
                db.add(
                    MaterialInbound(
                        inbound_no=pending_no,
                        material_id=first_material.id,
                        material_code=first_material.material_code,
                        material_name=first_material.material_name,
                        spec=first_material.spec,
                        quantity=100,
                        unit=first_material.unit,
                        warehouse_id=first_wh.id,
                        warehouse_name=first_wh.name,
                        location_id=first_loc.id if first_loc else None,
                        location_code=first_loc.location_code if first_loc else None,
                        inbound_date=date.today(),
                        handler="待确认",
                        status="pending",
                    )
                )

        db.commit()
    finally:
        db.close()


def seed_inspection_data():
    db = SessionLocal()
    try:
        if db.query(DeviceType).first():
            return

        types = [
            DeviceType(name="CNC加工中心", code="CNC"),
            DeviceType(name="注塑机", code="INJ"),
            DeviceType(name="包装线", code="PKG"),
        ]
        db.add_all(types)
        db.flush()

        devices = [
            Device(code="EQ-CNC-001", name="1号CNC加工中心", device_type_id=types[0].id, location="A车间"),
            Device(code="EQ-CNC-002", name="2号CNC加工中心", device_type_id=types[0].id, location="A车间"),
            Device(code="EQ-INJ-001", name="1号注塑机", device_type_id=types[1].id, location="B车间"),
            Device(code="EQ-INJ-002", name="2号注塑机", device_type_id=types[1].id, location="B车间"),
            Device(code="EQ-PKG-001", name="自动包装线", device_type_id=types[2].id, location="C车间"),
        ]
        db.add_all(devices)
        db.flush()

        plan_cnc = InspectionPlan(
            name="CNC日检计划",
            device_type_id=types[0].id,
            frequency_type="daily",
            is_active=True,
        )
        plan_cnc.items = [
            InspectionPlanItem(item_name="主轴温度", standard_value="≤60℃", judge_type="numeric", sort_order=0),
            InspectionPlanItem(item_name="润滑油位", standard_value="正常", judge_type="ok_ng", sort_order=1),
            InspectionPlanItem(item_name="冷却液浓度", standard_value="5-8%", judge_type="numeric", sort_order=2),
        ]
        plan_inj = InspectionPlan(
            name="注塑机周检计划",
            device_type_id=types[1].id,
            frequency_type="weekly",
            frequency_value=1,
            is_active=True,
        )
        plan_inj.items = [
            InspectionPlanItem(item_name="液压压力", standard_value="80-120bar", judge_type="numeric", sort_order=0),
            InspectionPlanItem(item_name="安全门联锁", standard_value="正常", judge_type="ok_ng", sort_order=1),
        ]
        db.add_all([plan_cnc, plan_inj])
        db.flush()

        today = date.today()
        records = [
            InspectionRecord(
                device_id=devices[0].id,
                plan_id=plan_cnc.id,
                inspector="张三",
                inspect_date=today,
                status="normal",
                remark="运行正常",
            ),
            InspectionRecord(
                device_id=devices[2].id,
                plan_id=plan_inj.id,
                inspector="李四",
                inspect_date=today,
                status="abnormal",
                remark="液压压力偏低",
            ),
            InspectionRecord(
                device_id=devices[1].id,
                plan_id=plan_cnc.id,
                inspector="王五",
                inspect_date=today - timedelta(days=1),
                status="normal",
            ),
        ]
        records[0].items = [
            InspectionRecordItem(item_name="主轴温度", standard_value="≤60℃", actual_value="52", result="OK"),
            InspectionRecordItem(item_name="润滑油位", standard_value="正常", result="OK"),
            InspectionRecordItem(item_name="冷却液浓度", standard_value="5-8%", actual_value="6.2", result="OK"),
        ]
        records[1].items = [
            InspectionRecordItem(item_name="液压压力", standard_value="80-120bar", actual_value="72", result="NG"),
            InspectionRecordItem(item_name="安全门联锁", standard_value="正常", result="OK"),
        ]
        records[2].items = [
            InspectionRecordItem(item_name="主轴温度", standard_value="≤60℃", actual_value="48", result="OK"),
            InspectionRecordItem(item_name="润滑油位", standard_value="正常", result="OK"),
        ]
        db.add_all(records)
        db.commit()
    finally:
        db.close()


def seed_equipment_data():
    db = SessionLocal()
    try:
        if db.query(Equipment).first():
            return

        samples = [
            Equipment(
                equipment_code="EQ-2024-001",
                name="1号CNC加工中心",
                spec_model="VMC-850",
                department="机加工车间",
                location="A区-01",
                status="运行",
                purchase_date=date(2022, 3, 15),
                commission_date=date(2022, 4, 1),
                supplier="沈阳机床",
            ),
            Equipment(
                equipment_code="EQ-2024-002",
                name="2号CNC加工中心",
                spec_model="VMC-850",
                department="机加工车间",
                location="A区-02",
                status="运行",
                purchase_date=date(2022, 3, 15),
                commission_date=date(2022, 4, 1),
                supplier="沈阳机床",
            ),
            Equipment(
                equipment_code="EQ-2024-003",
                name="1号注塑机",
                spec_model="HTF-160X1",
                department="注塑车间",
                location="B区-01",
                status="停机",
                purchase_date=date(2021, 8, 20),
                commission_date=date(2021, 9, 10),
                supplier="海天塑机",
            ),
            Equipment(
                equipment_code="EQ-2024-004",
                name="自动包装线",
                spec_model="PKG-A200",
                department="包装车间",
                location="C区-01",
                status="维修",
                purchase_date=date(2023, 1, 10),
                commission_date=date(2023, 2, 1),
                supplier="博世包装",
                remark="传送带待更换",
            ),
            Equipment(
                equipment_code="EQ-2023-015",
                name="老旧铣床",
                spec_model="XK5032",
                department="机加工车间",
                location="A区-旧区",
                status="报废",
                purchase_date=date(2010, 5, 1),
                commission_date=date(2010, 6, 1),
                supplier="北京第一机床厂",
                remark="已停用待处置",
            ),
        ]
        db.add_all(samples)
        db.commit()
    finally:
        db.close()


def seed_equipment_maintenance_data():
    db = SessionLocal()
    try:
        if db.query(EquipmentMaintenancePlan).first():
            return

        equipment_list = db.query(Equipment).limit(3).all()
        if not equipment_list:
            return

        def _equipment_id(preferred: int) -> int:
            idx = preferred if preferred < len(equipment_list) else 0
            return equipment_list[idx].id

        now = datetime.utcnow()
        plan1 = EquipmentMaintenancePlan(
            equipment_id=_equipment_id(0),
            name="CNC月度保养",
            cycle_type="month",
            cycle_value=1,
            items=[
                {
                    "item_name": "主轴润滑",
                    "check_method": "目视检查油位",
                    "standard": "油位在标线范围内",
                },
                {
                    "item_name": "导轨清洁",
                    "check_method": "清洁后目视",
                    "standard": "无切屑堆积、无锈蚀",
                },
            ],
            status="enabled",
            next_due_at=now + timedelta(days=2),
        )
        plan2 = EquipmentMaintenancePlan(
            equipment_id=_equipment_id(1),
            name="CNC周保养",
            cycle_type="week",
            cycle_value=1,
            items=[
                {
                    "item_name": "冷却液检测",
                    "check_method": "浓度计测量",
                    "standard": "浓度 5-8%",
                },
            ],
            status="enabled",
            next_due_at=now - timedelta(days=1),
        )
        db.add_all([plan1, plan2])
        db.flush()

        order1 = EquipmentMaintenanceOrder(
            plan_id=plan2.id,
            equipment_id=_equipment_id(1),
            order_no=f"MO-{now.strftime('%Y%m%d')}-0001",
            status="pending",
            planned_start_at=now - timedelta(days=1),
        )
        db.add(order1)
        db.commit()
    finally:
        db.close()


def seed_equipment_repair_data():
    db = SessionLocal()
    try:
        if db.query(EquipmentRepair).first():
            return

        equipment_list = db.query(Equipment).all()
        if not equipment_list:
            return

        def _equipment_id(preferred: int) -> int:
            """台账不足时回退到已有设备，避免启动种子 IndexError 导致后端起不来。"""
            idx = preferred if preferred < len(equipment_list) else 0
            return equipment_list[idx].id

        now = datetime.utcnow()

        # Repair 1: completed
        repair1 = EquipmentRepair(
            repair_no=f"RE-{now.strftime('%Y%m%d')}-0001",
            equipment_id=_equipment_id(2),  # 优先 1号注塑机 (停机)
            fault_category="液压故障",
            fault_description="注塑机液压系统压力不稳定，合模时出现异响，生产效率下降约30%",
            urgency="high",
            status="completed",
            reporter="李四",
            repair_person="王师傅",
            start_time=now - timedelta(days=3),
            repair_completed_at=now - timedelta(days=1),
            repair_description="更换液压泵密封圈，清洗液压阀组，重新校准系统压力至100bar",
            images=[],
        )
        repair1_parts = [
            EquipmentRepairPart(repair_id=None, part_name="液压泵密封圈", part_spec="Φ80×5.7", quantity=2, unit="套", unit_price=185.00),
            EquipmentRepairPart(repair_id=None, part_name="液压油滤芯", part_spec="HY-10-25", quantity=1, unit="个", unit_price=420.00),
            EquipmentRepairPart(repair_id=None, part_name="O型密封圈组", part_spec="NBR-90", quantity=4, unit="个", unit_price=25.00),
        ]
        repair1.parts = repair1_parts

        # Repair 2: in_progress
        repair2 = EquipmentRepair(
            repair_no=f"RE-{now.strftime('%Y%m%d')}-0002",
            equipment_id=_equipment_id(3),  # 优先 自动包装线 (维修)
            fault_category="传动故障",
            fault_description="包装线传送带跑偏严重，电机驱动辊筒磨损异响",
            urgency="urgent",
            status="in_progress",
            reporter="赵六",
            repair_person="张工",
            start_time=now - timedelta(hours=6),
            repair_completed_at=None,
            repair_description=None,
            images=[],
        )
        repair2_parts = [
            EquipmentRepairPart(repair_id=None, part_name="传送带", part_spec="PVC-1200×3", quantity=1, unit="条", unit_price=2800.00),
            EquipmentRepairPart(repair_id=None, part_name="驱动辊筒", part_spec="Φ89×1200", quantity=1, unit="根", unit_price=1560.00),
        ]
        repair2.parts = repair2_parts

        # Repair 3: pending
        repair3 = EquipmentRepair(
            repair_no=f"RE-{now.strftime('%Y%m%d')}-0003",
            equipment_id=_equipment_id(0),  # 优先 1号CNC加工中心 (运行)
            fault_category="控制系统故障",
            fault_description="CNC控制系统偶尔出现黑屏重启，怀疑主板供电模块异常",
            urgency="normal",
            status="pending",
            reporter="张三",
            repair_person=None,
            start_time=None,
            repair_completed_at=None,
            repair_description=None,
            images=[],
        )
        repair3_parts = []

        db.add_all([repair1, repair2, repair3])
        db.commit()
    finally:
        db.close()


def seed_quality_data():
    db = SessionLocal()
    try:
        if db.query(QualityMetrics).first():
            return

        lines = ["SMT-1线", "SMT-2线", "DIP线", "组装线", "测试线"]
        processes = ["贴片", "焊接", "AOI检测", "功能测试", "包装"]
        defect_types = ["虚焊", "短路", "元件偏移", "漏件", "外观不良", "功能异常", "尺寸偏差"]
        product_codes = ["PCB-A100", "PCB-A200", "PCB-B300", "PCB-C400", "PCB-D500"]
        today = date.today()

        metrics = []
        for day_offset in range(30):
            record_date = today - timedelta(days=29 - day_offset)
            for line in lines:
                for process in processes:
                    total = 800 + (day_offset * 3) + hash(f"{line}{process}") % 120
                    defect = int(total * (0.015 + (hash(record_date.isoformat() + line) % 8) / 1000))
                    scrap = int(total * (0.003 + (hash(process) % 5) / 2000))
                    good = total - defect - scrap
                    metrics.append(
                        QualityMetrics(
                            record_date=record_date,
                            production_line=line,
                            process=process,
                            good_count=max(good, 0),
                            defect_count=defect,
                            scrap_count=scrap,
                            total_inspected=total,
                        )
                    )
        db.add_all(metrics)

        anomalies = [
            QualityAnomaly(
                production_line="SMT-1线",
                process="焊接",
                defect_type="虚焊",
                severity="critical",
                status="open",
                discovered_at=datetime.utcnow() - timedelta(hours=2),
            ),
            QualityAnomaly(
                production_line="SMT-2线",
                process="AOI检测",
                defect_type="短路",
                severity="major",
                status="open",
                discovered_at=datetime.utcnow() - timedelta(hours=5),
            ),
            QualityAnomaly(
                production_line="DIP线",
                process="功能测试",
                defect_type="功能异常",
                severity="major",
                status="open",
                discovered_at=datetime.utcnow() - timedelta(hours=8),
            ),
            QualityAnomaly(
                production_line="组装线",
                process="包装",
                defect_type="外观不良",
                severity="minor",
                status="open",
                discovered_at=datetime.utcnow() - timedelta(hours=12),
            ),
            QualityAnomaly(
                production_line="测试线",
                process="功能测试",
                defect_type="尺寸偏差",
                severity="minor",
                status="processing",
                discovered_at=datetime.utcnow() - timedelta(days=1),
                handler="张工",
            ),
            QualityAnomaly(
                production_line="SMT-1线",
                process="贴片",
                defect_type="元件偏移",
                severity="major",
                status="closed",
                discovered_at=datetime.utcnow() - timedelta(days=2),
                handler="李工",
            ),
        ]
        db.add_all(anomalies)
        db.flush()

        defect_details = []
        for idx, dtype in enumerate(defect_types):
            for j in range(3):
                defect_details.append(
                    QualityDefectDetail(
                        anomaly_id=anomalies[idx % len(anomalies)].id if idx < 4 else None,
                        defect_type=dtype,
                        product_code=product_codes[(idx + j) % len(product_codes)],
                        quantity=120 - idx * 8 + j * 15,
                        production_line=lines[(idx + j) % len(lines)],
                        process=processes[(idx + j) % len(processes)],
                    )
                )
        db.add_all(defect_details)
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_work_orders_actual_start_time()
    ensure_work_orders_actual_end_time()
    ensure_work_orders_current_process()
    ensure_maintenance_orders_plan_complete_date()
    ensure_equipment_repairs_repair_completed_at()
    seed_default_user()
    seed_inspection_data()
    seed_equipment_data()
    seed_equipment_maintenance_data()
    seed_equipment_repair_data()
    seed_quality_data()
    seed_analytics_data()
    backfill_recent_operational_data()
    ensure_inventory_stock_backfill()
    ensure_material_inbound_backfill()
    yield


app = FastAPI(
    title="ERP 制造执行系统 API",
    description=(
        "江西中软 ERP / MES 后端接口文档。\n\n"
        "- 业务数据均从 SQLite 数据库查询/写入（见 `docs/DATABASE_SCHEMA.md`）\n"
        "- 除登录与健康检查外，接口需携带 JWT：`Authorization: Bearer <token>`\n"
        "- 在线调试：`/docs`（Swagger）或 `/redoc`"
    ),
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=OPENAPI_TAGS,
    )
    app.openapi_schema = apply_chinese_openapi(schema)
    return app.openapi_schema


app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "http://127.0.0.1:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(work_orders.router)
app.include_router(kanban_boards.router)
app.include_router(kanban_production.router)
app.include_router(kanban_general.router)
app.include_router(production.router)
app.include_router(devices.router)
app.include_router(inspection.router)
app.include_router(equipment.router)
app.include_router(equipment_maintenance.router)
app.include_router(equipment_repair.router)
app.include_router(device_dashboard.router)
app.include_router(quality.router)
app.include_router(reports.router)
app.include_router(warehouse.router)


@app.get("/api/health", tags=["系统"])
def health():
    """健康检查：确认服务可用。"""
    return {"status": "ok"}
