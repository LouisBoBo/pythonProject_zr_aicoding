"""客诉台账与 COPQ 金额：客户主数据 + 客诉成本字段。"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, inspect
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database import Base


class Customer(Base):
    """ERP 客户主数据（客诉/COPQ 依赖）。"""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    contact_person: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class CustomerComplaint(Base):
    """客户投诉台账（含 COPQ 成本字段）。"""

    __tablename__ = "customer_complaints"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    complaint_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    customer_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    complaint_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    complaint_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="质量"
    )  # 质量 / 交期 / 服务
    severity: Mapped[int] = mapped_column(Integer, nullable=False, default=3)  # 1-5
    product_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    product_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    affected_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # COPQ 成本字段
    cost_category: Mapped[str] = mapped_column(
        String(30), nullable=False, default="claim"
    )  # scrap / rework / return / claim
    unit_cost: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    copq_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="CNY")
    problem_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", index=True
    )  # open / processing / closed
    assigned_to: Mapped[str | None] = mapped_column(String(50), nullable=True)
    closed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


def ensure_copq_schema(bind_engine) -> None:
    """确保客户主数据与客诉表存在。"""
    inspector = inspect(bind_engine)
    if not inspector.has_table("customers"):
        Customer.__table__.create(bind=bind_engine, checkfirst=True)
    if not inspector.has_table("customer_complaints"):
        CustomerComplaint.__table__.create(bind=bind_engine, checkfirst=True)


# IPQC 高频客户码 → 演示客户名（补齐 ERP 客户字段）
_SEED_CUSTOMERS: list[dict] = [
    {"customer_code": "6901", "customer_name": "华东电子有限公司", "region": "华东", "contact_person": "张工"},
    {"customer_code": "6021", "customer_name": "南方智造股份", "region": "华南", "contact_person": "李工"},
    {"customer_code": "6685", "customer_name": "北方精密科技", "region": "华北", "contact_person": "王工"},
    {"customer_code": "7031", "customer_name": "西部自动化集团", "region": "西北", "contact_person": "赵工"},
    {"customer_code": "9012", "customer_name": "中原装备制造", "region": "华中", "contact_person": "刘工"},
    {"customer_code": "7026", "customer_name": "海河电子科技", "region": "华北", "contact_person": "陈工"},
    {"customer_code": "2266", "customer_name": "粤海智能终端", "region": "华南", "contact_person": "黄工"},
    {"customer_code": "6019", "customer_name": "川渝机电股份", "region": "西南", "contact_person": "周工"},
]


def seed_copq_data(db: Session) -> None:
    """写入演示客户与客诉/COPQ 记录（幂等）。"""
    if db.query(Customer).count() == 0:
        for row in _SEED_CUSTOMERS:
            db.add(
                Customer(
                    customer_code=row["customer_code"],
                    customer_name=row["customer_name"],
                    contact_person=row.get("contact_person"),
                    region=row.get("region"),
                    contact_phone="1380000" + row["customer_code"][-4:],
                    status="active",
                )
            )
        db.commit()

    if db.query(CustomerComplaint).count() > 0:
        return

    customers = {c.customer_code: c for c in db.query(Customer).all()}
    today = date.today()
    samples = [
        ("6901", "质量", "claim", "PCB-2024-A", "铝基板 PCB", 120, 18.6, 4, 12),
        ("6901", "质量", "rework", "PCB-2024-A", "铝基板 PCB", 80, 6.2, 3, 25),
        ("6021", "质量", "return", "IC-STM32F407", "STM32F407VET6", 40, 26.8, 5, 8),
        ("6021", "交期", "claim", "CONN-USB-C", "USB-C 连接器", 200, 1.85, 2, 18),
        ("6685", "质量", "scrap", "HEATSINK-40", "铝散热片", 150, 2.4, 3, 5),
        ("7031", "质量", "claim", "LED-5050-W", "白光 LED 5050", 500, 0.16, 2, 15),
        ("9012", "服务", "claim", "HEADER-254", "排针 2.54mm", 1000, 0.28, 1, 30),
        ("7026", "质量", "rework", "CAP-0603-1UF", "贴片电容 1μF", 300, 0.035, 3, 10),
        ("2266", "质量", "return", "RES-0805-10K", "贴片电阻 10KΩ", 800, 0.012, 2, 22),
        ("6019", "质量", "scrap", "IND-4R7", "功率电感 4.7μH", 60, 0.42, 4, 3),
        ("6901", "质量", "claim", "DIODE-1N4148", "开关二极管 1N4148", 2000, 0.018, 3, 40),
        ("6685", "交期", "claim", "PCB-2024-A", "铝基板 PCB", 50, 18.6, 4, 2),
    ]
    for i, (code, ctype, cat, pcode, pname, qty, unit, sev, days_ago) in enumerate(samples, start=1):
        cust = customers.get(code)
        amount = round(float(qty) * float(unit), 2)
        db.add(
            CustomerComplaint(
                complaint_no=f"CC{today.strftime('%Y%m')}{i:04d}",
                customer_id=cust.id if cust else None,
                customer_code=code,
                customer_name=cust.customer_name if cust else code,
                complaint_date=today - timedelta(days=days_ago),
                complaint_type=ctype,
                severity=sev,
                product_code=pcode,
                product_name=pname,
                affected_qty=qty,
                cost_category=cat,
                unit_cost=unit,
                copq_amount=amount,
                problem_description=f"演示客诉：{ctype}/{cat}，影响 {qty} 件",
                status="closed" if days_ago > 20 else ("processing" if days_ago > 7 else "open"),
                assigned_to="品质部",
                closed_date=(today - timedelta(days=days_ago - 5)) if days_ago > 20 else None,
            )
        )
    db.commit()
