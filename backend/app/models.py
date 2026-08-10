from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    product_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    production_line: Mapped[str | None] = mapped_column(String(50), nullable=True)
    plan_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    assignee: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class KanbanBoard(Base):
    __tablename__ = "kanban_boards"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    board_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    board_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="production")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    production_line: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class DeviceType(Base):
    __tablename__ = "device_types"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    devices: Mapped[list["Device"]] = relationship(back_populates="device_type")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type_id: Mapped[int] = mapped_column(ForeignKey("device_types.id"), nullable=False)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    device_type: Mapped["DeviceType"] = relationship(back_populates="devices")
    inspection_records: Mapped[list["InspectionRecord"]] = relationship(
        back_populates="device"
    )


class InspectionPlan(Base):
    __tablename__ = "inspection_plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type_id: Mapped[int | None] = mapped_column(ForeignKey("device_types.id"), nullable=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    frequency_type: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")
    frequency_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cron_expr: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    items: Mapped[list["InspectionPlanItem"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="InspectionPlanItem.sort_order"
    )
    device_type: Mapped["DeviceType | None"] = relationship()
    device: Mapped["Device | None"] = relationship()
    records: Mapped[list["InspectionRecord"]] = relationship(back_populates="plan")


class InspectionPlanItem(Base):
    __tablename__ = "inspection_plan_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("inspection_plans.id"), nullable=False)
    item_name: Mapped[str] = mapped_column(String(100), nullable=False)
    standard_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    judge_type: Mapped[str] = mapped_column(String(20), nullable=False, default="ok_ng")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    plan: Mapped["InspectionPlan"] = relationship(back_populates="items")


class InspectionRecord(Base):
    __tablename__ = "inspection_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("inspection_plans.id"), nullable=True)
    inspector: Mapped[str] = mapped_column(String(50), nullable=False)
    inspect_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    device: Mapped["Device"] = relationship(back_populates="inspection_records")
    plan: Mapped["InspectionPlan | None"] = relationship(back_populates="records")
    items: Mapped[list["InspectionRecordItem"]] = relationship(
        back_populates="record", cascade="all, delete-orphan"
    )


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    equipment_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    spec_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="运行")
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    commission_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    supplier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class InspectionRecordItem(Base):
    __tablename__ = "inspection_record_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("inspection_records.id"), nullable=False)
    item_name: Mapped[str] = mapped_column(String(100), nullable=False)
    standard_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actual_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    result: Mapped[str | None] = mapped_column(String(10), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)

    record: Mapped["InspectionRecord"] = relationship(back_populates="items")
