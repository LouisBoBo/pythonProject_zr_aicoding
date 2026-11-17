"""综合看板 API — 五大模块从领域表聚合。"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Equipment,
    EquipmentAlarm,
    EquipmentOeeSnapshot,
    EquipmentRepair,
    InventoryBalance,
    InventoryTransaction,
    Material,
    ProductionLine,
    ProductionOutputRecord,
    ProductionPlan,
    QualityDefectDetail,
    QualityMetrics,
    SalesOrder,
    ShipmentRecord,
    User,
    WorkOrder,
)
from app.schemas import (
    CompKanbanDefectItem,
    CompKanbanDeviceAlert,
    CompKanbanDeviceCard,
    CompKanbanDeviceMonitor,
    CompKanbanLineStatus,
    CompKanbanMaterialInventory,
    CompKanbanMaterialItem,
    CompKanbanOrderDelivery,
    CompKanbanOverdueOrder,
    CompKanbanProductionProgress,
    CompKanbanQualityOverview,
    CompKanbanShipmentStats,
    CompKanbanStatusPie,
    CompKanbanTrendPoint,
    ComprehensiveKanbanResponse,
)

router = APIRouter(prefix="/api/kanban", tags=["kanban-general"])

STATUS_COLORS = {
    "运行": "#52c41a",
    "待机": "#faad14",
    "维修": "#fa8c16",
    "停机": "#ff4d4f",
}


def _production_progress(db: Session) -> CompKanbanProductionProgress:
    active = db.query(WorkOrder).filter(WorkOrder.status == "in_progress").count()
    today = date.today()
    plan = int(
        db.query(func.coalesce(func.sum(ProductionPlan.plan_qty), 0))
        .filter(ProductionPlan.plan_date == today)
        .scalar()
        or 0
    )
    actual = int(
        db.query(func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0))
        .filter(ProductionOutputRecord.record_at >= datetime.combine(today, datetime.min.time()))
        .scalar()
        or 0
    )
    completion_rate = round(actual / plan * 100, 1) if plan else 0

    trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        p = int(
            db.query(func.coalesce(func.sum(ProductionPlan.plan_qty), 0))
            .filter(ProductionPlan.plan_date == d)
            .scalar()
            or 0
        )
        a = int(
            db.query(func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0))
            .filter(
                ProductionOutputRecord.record_at >= datetime.combine(d, datetime.min.time()),
                ProductionOutputRecord.record_at
                < datetime.combine(d + timedelta(days=1), datetime.min.time()),
            )
            .scalar()
            or 0
        )
        trend.append(
            CompKanbanTrendPoint(
                label=d.strftime("%m-%d"),
                value=round(a / p * 100, 1) if p else 0,
            )
        )

    line_status = []
    for ln in db.query(ProductionLine).order_by(ProductionLine.id).all():
        in_prod = (
            db.query(WorkOrder)
            .filter(
                WorkOrder.production_line == ln.name,
                WorkOrder.status == "in_progress",
            )
            .count()
        )
        completed = (
            db.query(WorkOrder)
            .filter(
                WorkOrder.production_line == ln.name,
                WorkOrder.status.in_(["completed", "closed"]),
            )
            .count()
        )
        pending = (
            db.query(WorkOrder)
            .filter(WorkOrder.production_line == ln.name, WorkOrder.status == "pending")
            .count()
        )
        line_status.append(
            CompKanbanLineStatus(
                line_name=ln.name,
                in_production=in_prod,
                completed=completed,
                pending=pending,
            )
        )

    return CompKanbanProductionProgress(
        active_orders=active,
        completion_rate=completion_rate,
        schedule_achievement_trend=trend,
        line_status=line_status,
    )


def _quality_overview(db: Session) -> CompKanbanQualityOverview:
    today = date.today()
    yield_trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        rows = db.query(QualityMetrics).filter(QualityMetrics.record_date == d).all()
        inspected = sum(r.total_inspected for r in rows) or 1
        good = sum(r.good_count for r in rows)
        yield_trend.append(
            CompKanbanTrendPoint(label=d.strftime("%m-%d"), value=round(good / inspected * 100, 1))
        )

    recent = (
        db.query(QualityMetrics)
        .filter(QualityMetrics.record_date >= today - timedelta(days=6))
        .all()
    )
    inspected = sum(r.total_inspected for r in recent) or 1
    good = sum(r.good_count for r in recent)
    first_pass = round(good / inspected * 100, 1)

    # 良率目标：取近 30 日 quality_metrics 平均良率作为运行目标基线（纯库内数据）
    month_rows = (
        db.query(QualityMetrics)
        .filter(QualityMetrics.record_date >= today - timedelta(days=29))
        .all()
    )
    m_inspected = sum(r.total_inspected for r in month_rows) or 0
    m_good = sum(r.good_count for r in month_rows)
    yield_target = round(m_good / m_inspected * 100, 1) if m_inspected else first_pass

    dist = (
        db.query(QualityDefectDetail.defect_type, func.sum(QualityDefectDetail.quantity))
        .group_by(QualityDefectDetail.defect_type)
        .order_by(func.sum(QualityDefectDetail.quantity).desc())
        .limit(5)
        .all()
    )
    defect_distribution = [
        CompKanbanDefectItem(name=name or "其它", value=int(qty or 0)) for name, qty in dist
    ]

    return CompKanbanQualityOverview(
        yield_trend=yield_trend,
        yield_target=yield_target,
        first_pass_rate=first_pass,
        defect_distribution=defect_distribution,
    )


def _device_monitor(db: Session) -> CompKanbanDeviceMonitor:
    today = date.today()
    equipment = db.query(Equipment).order_by(Equipment.id).limit(8).all()
    devices = []
    for eq in equipment:
        snap = (
            db.query(EquipmentOeeSnapshot)
            .filter(
                EquipmentOeeSnapshot.equipment_id == eq.id,
                EquipmentOeeSnapshot.period_type == "day",
            )
            .order_by(EquipmentOeeSnapshot.period_start.desc())
            .first()
        )
        devices.append(
            CompKanbanDeviceCard(
                code=eq.equipment_code,
                name=eq.name,
                utilization=float(snap.availability) if snap else 0,
                status=eq.status,
            )
        )

    status_rows = (
        db.query(Equipment.status, func.count(Equipment.id)).group_by(Equipment.status).all()
    )
    status_distribution = [
        CompKanbanStatusPie(
            name=status,
            value=count,
            color=STATUS_COLORS.get(status, "#909399"),
        )
        for status, count in status_rows
    ]

    alerts = []
    # prefer open repairs, then recent alarms
    repairs = (
        db.query(EquipmentRepair)
        .filter(EquipmentRepair.status.in_(["pending", "in_progress"]))
        .order_by(EquipmentRepair.id.desc())
        .limit(5)
        .all()
    )
    for r in repairs:
        eq = db.query(Equipment).filter(Equipment.id == r.equipment_id).first()
        alerts.append(
            CompKanbanDeviceAlert(
                id=r.id,
                device_code=eq.equipment_code if eq else "",
                device_name=eq.name if eq else "",
                alert_type=r.fault_category,
                severity=r.urgency,
                time=(r.start_time or r.created_at).strftime("%H:%M"),
                description=r.fault_description[:80],
            )
        )
    if len(alerts) < 3:
        for alarm in (
            db.query(EquipmentAlarm)
            .order_by(EquipmentAlarm.occurred_at.desc())
            .limit(5 - len(alerts))
            .all()
        ):
            eq = db.query(Equipment).filter(Equipment.id == alarm.equipment_id).first()
            alerts.append(
                CompKanbanDeviceAlert(
                    id=alarm.id,
                    device_code=eq.equipment_code if eq else "",
                    device_name=eq.name if eq else "",
                    alert_type=alarm.alarm_type,
                    severity=alarm.severity,
                    time=alarm.occurred_at.strftime("%H:%M"),
                    description=(alarm.description or "")[:80],
                )
            )

    return CompKanbanDeviceMonitor(
        devices=devices,
        status_distribution=status_distribution,
        alerts=alerts,
    )


def _order_delivery(db: Session) -> CompKanbanOrderDelivery:
    today = date.today()
    orders = db.query(SalesOrder).all()
    on_time = sum(1 for o in orders if o.shipped_qty >= o.plan_qty or o.due_date >= today)
    delivery_rate = round(on_time / len(orders) * 100, 1) if orders else 0

    monthly_trend = []
    for m in range(7, -1, -1):
        # approximate by month offset using shipment sums
        ref = (today.replace(day=1) - timedelta(days=30 * m)).replace(day=1)
        next_m = (ref + timedelta(days=32)).replace(day=1)
        shipped = int(
            db.query(func.coalesce(func.sum(ShipmentRecord.ship_qty), 0))
            .filter(
                ShipmentRecord.shipped_at >= datetime.combine(ref, datetime.min.time()),
                ShipmentRecord.shipped_at < datetime.combine(next_m, datetime.min.time()),
            )
            .scalar()
            or 0
        )
        planned = sum(
            o.plan_qty
            for o in orders
            if ref <= o.due_date < next_m
        ) or 1
        # use shipment vs plan as rate proxy
        monthly_trend.append(
            CompKanbanTrendPoint(
                label=f"{ref.month}月",
                value=min(100.0, round(shipped / planned * 100, 1)),
            )
        )

    overdue = (
        db.query(SalesOrder)
        .filter(SalesOrder.due_date < today, SalesOrder.status != "closed")
        .order_by(SalesOrder.due_date.asc())
        .limit(5)
        .all()
    )
    overdue_orders = [
        CompKanbanOverdueOrder(
            order_no=o.order_no,
            customer=o.customer,
            overdue_days=(today - o.due_date).days,
            status=o.status,
        )
        for o in overdue
    ]

    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    this_week = int(
        db.query(func.coalesce(func.sum(ShipmentRecord.ship_qty), 0))
        .filter(ShipmentRecord.shipped_at >= datetime.combine(week_start, datetime.min.time()))
        .scalar()
        or 0
    )
    this_month = int(
        db.query(func.coalesce(func.sum(ShipmentRecord.ship_qty), 0))
        .filter(ShipmentRecord.shipped_at >= datetime.combine(month_start, datetime.min.time()))
        .scalar()
        or 0
    )

    return CompKanbanOrderDelivery(
        delivery_rate=delivery_rate,
        monthly_trend=monthly_trend,
        overdue_orders=overdue_orders,
        shipment_stats=CompKanbanShipmentStats(this_week=this_week, this_month=this_month),
    )


def _material_inventory(db: Session) -> CompKanbanMaterialInventory:
    materials = db.query(Material).order_by(Material.id).all()
    critical = []
    shortage_alerts = []
    for m in materials[:8]:
        qty = int(
            db.query(func.coalesce(func.sum(InventoryBalance.quantity), 0))
            .filter(InventoryBalance.material_id == m.id)
            .scalar()
            or 0
        )
        if qty < m.safety_stock:
            status = "shortage"
            shortage_alerts.append(
                f"{m.material_name} 库存仅{qty}单位，低于安全线{m.safety_stock}"
            )
        elif qty < m.safety_stock * 1.2:
            status = "warning"
            shortage_alerts.append(f"{m.material_name} 库存接近安全线，建议本周补货")
        else:
            status = "normal"
        critical.append(
            CompKanbanMaterialItem(
                name=m.material_name,
                current_stock=float(qty),
                safety_line=float(m.safety_stock),
                max_stock=float(m.max_stock),
                status=status,
            )
        )

    # 周转天数趋势：按周从库存流水反推时点库存与出库量计算
    # 周转天数 ≈ 时点库存 / 日均出库量
    turnover = []
    today = date.today()
    current_stock = int(
        db.query(func.coalesce(func.sum(InventoryBalance.quantity), 0)).scalar() or 0
    )
    for week_back in range(7, -1, -1):
        week_end = today - timedelta(days=week_back * 7)
        week_start = week_end - timedelta(days=6)
        start_dt = datetime.combine(week_start, datetime.min.time())
        end_dt = datetime.combine(week_end + timedelta(days=1), datetime.min.time())

        outbound = int(
            db.query(func.coalesce(func.sum(InventoryTransaction.quantity), 0))
            .filter(
                InventoryTransaction.txn_type == "out",
                InventoryTransaction.txn_at >= start_dt,
                InventoryTransaction.txn_at < end_dt,
            )
            .scalar()
            or 0
        )
        # 用「当前库存 - 之后入库 + 之后出库」估算该周末库存
        after_start = end_dt
        inbound_after = int(
            db.query(func.coalesce(func.sum(InventoryTransaction.quantity), 0))
            .filter(
                InventoryTransaction.txn_type == "in",
                InventoryTransaction.txn_at >= after_start,
            )
            .scalar()
            or 0
        )
        outbound_after = int(
            db.query(func.coalesce(func.sum(InventoryTransaction.quantity), 0))
            .filter(
                InventoryTransaction.txn_type == "out",
                InventoryTransaction.txn_at >= after_start,
            )
            .scalar()
            or 0
        )
        stock_then = max(0, current_stock - inbound_after + outbound_after)
        daily_out = outbound / 7.0
        days = round(stock_then / daily_out, 1) if daily_out > 0 else 0.0
        turnover.append(
            CompKanbanTrendPoint(label=f"第{8 - week_back}周", value=days)
        )

    return CompKanbanMaterialInventory(
        critical_materials=critical,
        shortage_alerts=shortage_alerts[:5],
        turnover_days_trend=turnover,
    )


@router.get("/general", response_model=ComprehensiveKanbanResponse)
def get_comprehensive_kanban(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ComprehensiveKanbanResponse(
        production_progress=_production_progress(db),
        quality_overview=_quality_overview(db),
        device_monitor=_device_monitor(db),
        order_delivery=_order_delivery(db),
        material_inventory=_material_inventory(db),
    )
