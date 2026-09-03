from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
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
    actual_start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_process: Mapped[str | None] = mapped_column(String(50), nullable=True)
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

    maintenance_plans: Mapped[list["EquipmentMaintenancePlan"]] = relationship(
        back_populates="equipment"
    )
    maintenance_orders: Mapped[list["EquipmentMaintenanceOrder"]] = relationship(
        back_populates="equipment"
    )
    repairs: Mapped[list["EquipmentRepair"]] = relationship(
        back_populates="equipment"
    )
    runtime_logs: Mapped[list["EquipmentRuntimeLog"]] = relationship(
        back_populates="equipment"
    )
    oee_snapshots: Mapped[list["EquipmentOeeSnapshot"]] = relationship(
        back_populates="equipment"
    )
    alarms: Mapped[list["EquipmentAlarm"]] = relationship(
        back_populates="equipment"
    )
    output_records: Mapped[list["EquipmentOutputRecord"]] = relationship(
        back_populates="equipment"
    )


class EquipmentMaintenancePlan(Base):
    __tablename__ = "equipment_maintenance_plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    cycle_type: Mapped[str] = mapped_column(String(20), nullable=False, default="day")
    cycle_value: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="enabled")
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    equipment: Mapped["Equipment"] = relationship(back_populates="maintenance_plans")
    orders: Mapped[list["EquipmentMaintenanceOrder"]] = relationship(
        back_populates="plan"
    )


class EquipmentMaintenanceOrder(Base):
    __tablename__ = "equipment_maintenance_orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("equipment_maintenance_plans.id"), nullable=True
    )
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    order_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    assignee: Mapped[str | None] = mapped_column(String(50), nullable=True)
    planned_start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    plan_complete_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    executor: Mapped[str | None] = mapped_column(String(50), nullable=True)
    results: Mapped[list | None] = mapped_column(JSON, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    plan: Mapped["EquipmentMaintenancePlan | None"] = relationship(back_populates="orders")
    equipment: Mapped["Equipment"] = relationship(back_populates="maintenance_orders")


class EquipmentRepair(Base):
    """设备维修工单"""
    __tablename__ = "equipment_repairs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    repair_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    fault_category: Mapped[str] = mapped_column(String(50), nullable=False, default="机械故障")
    fault_description: Mapped[str] = mapped_column(Text, nullable=False)
    urgency: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reporter: Mapped[str] = mapped_column(String(50), nullable=False)
    repair_person: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    repair_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    repair_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    images: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    equipment: Mapped["Equipment"] = relationship(back_populates="repairs")
    parts: Mapped[list["EquipmentRepairPart"]] = relationship(
        back_populates="repair", cascade="all, delete-orphan"
    )


class EquipmentRepairPart(Base):
    """维修更换配件"""
    __tablename__ = "equipment_repair_parts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    repair_id: Mapped[int] = mapped_column(ForeignKey("equipment_repairs.id"), nullable=False)
    part_name: Mapped[str] = mapped_column(String(100), nullable=False)
    part_spec: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="个")
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    repair: Mapped["EquipmentRepair"] = relationship(back_populates="parts")


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


class QualityMetrics(Base):
    __tablename__ = "quality_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    production_line: Mapped[str] = mapped_column(String(50), nullable=False)
    process: Mapped[str] = mapped_column(String(50), nullable=False)
    good_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    defect_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scrap_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_inspected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class QualityAnomaly(Base):
    __tablename__ = "quality_anomalies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    production_line: Mapped[str] = mapped_column(String(50), nullable=False)
    process: Mapped[str] = mapped_column(String(50), nullable=False)
    defect_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="minor")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    discovered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    handler: Mapped[str | None] = mapped_column(String(50), nullable=True)

    defect_details: Mapped[list["QualityDefectDetail"]] = relationship(
        back_populates="anomaly", cascade="all, delete-orphan"
    )


class QualityDefectDetail(Base):
    __tablename__ = "quality_defect_details"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    anomaly_id: Mapped[int | None] = mapped_column(ForeignKey("quality_anomalies.id"), nullable=True)
    defect_type: Mapped[str] = mapped_column(String(50), nullable=False)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    production_line: Mapped[str | None] = mapped_column(String(50), nullable=True)
    process: Mapped[str | None] = mapped_column(String(50), nullable=True)

    anomaly: Mapped["QualityAnomaly | None"] = relationship(back_populates="defect_details")


# ============================================================
#  生产主数据与事实表
# ============================================================


class ProductionLine(Base):
    """产线主数据"""

    __tablename__ = "production_lines"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    workshop: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    products: Mapped[list["Product"]] = relationship(back_populates="default_line")
    plans: Mapped[list["ProductionPlan"]] = relationship(back_populates="production_line")
    output_records: Mapped[list["ProductionOutputRecord"]] = relationship(
        back_populates="production_line"
    )
    wip_snapshots: Mapped[list["WipSnapshot"]] = relationship(back_populates="production_line")
    capacity_snapshots: Mapped[list["LineCapacitySnapshot"]] = relationship(
        back_populates="production_line"
    )


class Product(Base):
    """产品主数据"""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="件")
    default_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("production_lines.id"), nullable=True
    )

    default_line: Mapped["ProductionLine | None"] = relationship(back_populates="products")


class ProductionPlan(Base):
    """生产计划（按日/产线/产品）"""

    __tablename__ = "production_plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    plan_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    production_line_id: Mapped[int] = mapped_column(
        ForeignKey("production_lines.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    plan_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    production_line: Mapped["ProductionLine"] = relationship(back_populates="plans")
    product: Mapped["Product"] = relationship()


class ProductionOutputRecord(Base):
    """产量事实表"""

    __tablename__ = "production_output_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    record_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    production_line_id: Mapped[int] = mapped_column(
        ForeignKey("production_lines.id"), nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    work_order_id: Mapped[int | None] = mapped_column(ForeignKey("work_orders.id"), nullable=True)
    process_card_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    actual_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    area_output: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    defect_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    incoming_boards: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    production_line: Mapped["ProductionLine"] = relationship(back_populates="output_records")
    product: Mapped["Product | None"] = relationship()


class WipSnapshot(Base):
    """在制品快照"""

    __tablename__ = "wip_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    production_line_id: Mapped[int] = mapped_column(
        ForeignKey("production_lines.id"), nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # 待投料/在制/待检验/待入库
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    production_line: Mapped["ProductionLine"] = relationship(back_populates="wip_snapshots")
    product: Mapped["Product | None"] = relationship()


class LineCapacitySnapshot(Base):
    """产线/工位负荷快照"""

    __tablename__ = "line_capacity_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    production_line_id: Mapped[int] = mapped_column(
        ForeignKey("production_lines.id"), nullable=False
    )
    station_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    load_rate: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    capacity_utilization: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)

    production_line: Mapped["ProductionLine"] = relationship(back_populates="capacity_snapshots")


# ============================================================
#  设备遥测 / OEE / 告警
# ============================================================


class EquipmentRuntimeLog(Base):
    """设备运行时段日志"""

    __tablename__ = "equipment_runtime_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # 运行/停机/待机/维修
    runtime_hours: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    equipment: Mapped["Equipment"] = relationship(back_populates="runtime_logs")


class EquipmentOeeSnapshot(Base):
    """设备 OEE 快照"""

    __tablename__ = "equipment_oee_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)  # day/week/month
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    availability: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    performance: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    quality: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    oee: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)

    equipment: Mapped["Equipment"] = relationship(back_populates="oee_snapshots")


class EquipmentAlarm(Base):
    """设备告警"""

    __tablename__ = "equipment_alarms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    alarm_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    equipment: Mapped["Equipment"] = relationship(back_populates="alarms")


class EquipmentOutputRecord(Base):
    """设备产量记录"""

    __tablename__ = "equipment_output_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    output_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    equipment: Mapped["Equipment"] = relationship(back_populates="output_records")


# ============================================================
#  仓储
# ============================================================


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    locations: Mapped[list["WarehouseLocation"]] = relationship(back_populates="warehouse")


class WarehouseLocation(Base):
    __tablename__ = "warehouse_locations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    location_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="free")  # occupied/free/abnormal

    warehouse: Mapped["Warehouse"] = relationship(back_populates="locations")
    balances: Mapped[list["InventoryBalance"]] = relationship(back_populates="location")


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    material_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    material_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="其他")
    spec: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="件")
    safety_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    balances: Mapped[list["InventoryBalance"]] = relationship(back_populates="material")
    transactions: Mapped[list["InventoryTransaction"]] = relationship(back_populates="material")


class InventoryBalance(Base):
    __tablename__ = "inventory_balances"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False)
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouse_locations.id"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    material: Mapped["Material"] = relationship(back_populates="balances")
    location: Mapped["WarehouseLocation | None"] = relationship(back_populates="balances")


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False)
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouse_locations.id"), nullable=True
    )
    txn_type: Mapped[str] = mapped_column(String(20), nullable=False)  # in/out/move/check
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    txn_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    ref_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)

    material: Mapped["Material"] = relationship(back_populates="transactions")
    location: Mapped["WarehouseLocation | None"] = relationship()


class InventoryStock(Base):
    """物料库存汇总（按物料 + 仓库维度，关联物料主数据）"""

    __tablename__ = "inventory_stock"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False, index=True)
    material_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    material_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    warehouse_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="件")
    safety_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    material: Mapped["Material"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()


class MaterialInbound(Base):
    """物料入库单"""

    __tablename__ = "material_inbounds"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    inbound_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False, index=True)
    material_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    material_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    spec: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="件")
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    warehouse_name: Mapped[str] = mapped_column(String(100), nullable=False)
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouse_locations.id"), nullable=True
    )
    location_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    inbound_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    handler: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )  # pending=待入库, completed=已入库
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    material: Mapped["Material"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()
    location: Mapped["WarehouseLocation | None"] = relationship()


# ============================================================
#  销售订单 / 发货
# ============================================================


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    customer: Mapped[str] = mapped_column(String(100), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    plan_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shipped_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    shipments: Mapped[list["ShipmentRecord"]] = relationship(back_populates="sales_order")


class ShipmentRecord(Base):
    __tablename__ = "shipment_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"), nullable=False)
    ship_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shipped_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    sales_order: Mapped["SalesOrder"] = relationship(back_populates="shipments")


class Message(Base):
    """消息中心"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="system")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    link: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )


class EmployeeWorkHour(Base):
    """员工工时填报记录"""

    __tablename__ = "employee_work_hours"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_no: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    employee_name: Mapped[str] = mapped_column(String(50), nullable=False)
    department: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task_name: Mapped[str] = mapped_column(String(100), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    work_hours: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    overtime_hours: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    approval_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending / approved / rejected
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


class DashboardTodo(Base):
    """工作台待办"""

    __tablename__ = "dashboard_todos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    link: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
