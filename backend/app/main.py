from contextlib import asynccontextmanager

from datetime import date, datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
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
    QualityAnomaly,
    QualityDefectDetail,
    QualityMetrics,
    User,
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
    work_orders,
)


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

        now = datetime.utcnow()
        plan1 = EquipmentMaintenancePlan(
            equipment_id=equipment_list[0].id,
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
            equipment_id=equipment_list[1].id,
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
            equipment_id=equipment_list[1].id,
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

        now = datetime.utcnow()

        # Repair 1: completed
        repair1 = EquipmentRepair(
            repair_no=f"RE-{now.strftime('%Y%m%d')}-0001",
            equipment_id=equipment_list[2].id,  # 1号注塑机 (停机)
            fault_category="液压故障",
            fault_description="注塑机液压系统压力不稳定，合模时出现异响，生产效率下降约30%",
            urgency="high",
            status="completed",
            reporter="李四",
            repair_person="王师傅",
            start_time=now - timedelta(days=3),
            completion_time=now - timedelta(days=1),
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
            equipment_id=equipment_list[3].id,  # 自动包装线 (维修)
            fault_category="传动故障",
            fault_description="包装线传送带跑偏严重，电机驱动辊筒磨损异响",
            urgency="urgent",
            status="in_progress",
            reporter="赵六",
            repair_person="张工",
            start_time=now - timedelta(hours=6),
            completion_time=None,
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
            equipment_id=equipment_list[0].id,  # 1号CNC加工中心 (运行)
            fault_category="控制系统故障",
            fault_description="CNC控制系统偶尔出现黑屏重启，怀疑主板供电模块异常",
            urgency="normal",
            status="pending",
            reporter="张三",
            repair_person=None,
            start_time=None,
            completion_time=None,
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
    seed_default_user()
    seed_inspection_data()
    seed_equipment_data()
    seed_equipment_maintenance_data()
    seed_equipment_repair_data()
    seed_quality_data()
    yield


app = FastAPI(title="ERP System API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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


@app.get("/api/health")
def health():
    return {"status": "ok"}
