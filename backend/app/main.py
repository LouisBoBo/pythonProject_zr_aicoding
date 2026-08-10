from contextlib import asynccontextmanager

from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models import (
    Device,
    DeviceType,
    InspectionPlan,
    InspectionPlanItem,
    InspectionRecord,
    InspectionRecordItem,
    User,
)
from app.routers import auth, dashboard, devices, inspection, kanban_boards, kanban_production, production, work_orders


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_default_user()
    seed_inspection_data()
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
app.include_router(production.router)
app.include_router(devices.router)
app.include_router(inspection.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
