"""首页仪表盘 + 工作台汇总 — 从工单 / 产量 / 品质 / 待办表聚合。"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    DashboardTodo,
    InventoryStock,
    Message,
    ProductionOutputRecord,
    ProductionPlan,
    QualityAnomaly,
    User,
    WorkOrder,
)
from app.schemas import (
    AnomalySegment,
    DashboardResponse,
    DashboardStatItem,
    HourlyStats,
    ManufacturingDashboard,
    ProductionTrendPoint,
    TodoItem,
    WorkbenchCard,
    WorkbenchResponse,
    WorkbenchTodoItem,
    WorkOrderStatusItem,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

STATUS_LABEL = {
    "pending": "待处理",
    "in_progress": "进行中",
    "completed": "已完成",
    "closed": "已关闭",
}


def _manufacturing(db: Session) -> ManufacturingDashboard:
    today = date.today()
    month_start = today.replace(day=1)
    last_month_end = month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    monthly_output = int(
        db.query(func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0))
        .filter(ProductionOutputRecord.record_at >= datetime.combine(month_start, datetime.min.time()))
        .scalar()
        or 0
    )
    last_month_output = int(
        db.query(func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0))
        .filter(
            ProductionOutputRecord.record_at
            >= datetime.combine(last_month_start, datetime.min.time()),
            ProductionOutputRecord.record_at
            < datetime.combine(month_start, datetime.min.time()),
        )
        .scalar()
        or 0
    )
    daily_current = int(
        db.query(func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0))
        .filter(ProductionOutputRecord.record_at >= datetime.combine(today, datetime.min.time()))
        .scalar()
        or 0
    )
    daily_target = int(
        db.query(func.coalesce(func.sum(ProductionPlan.plan_qty), 0))
        .filter(ProductionPlan.plan_date == today)
        .scalar()
        or 0
    ) or max(daily_current, 1)

    # last 12 days efficiency trend (daily output)
    efficiency_trend = []
    for i in range(11, -1, -1):
        d = today - timedelta(days=i)
        qty = int(
            db.query(func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0))
            .filter(
                ProductionOutputRecord.record_at >= datetime.combine(d, datetime.min.time()),
                ProductionOutputRecord.record_at
                < datetime.combine(d + timedelta(days=1), datetime.min.time()),
            )
            .scalar()
            or 0
        )
        efficiency_trend.append(qty)

    open_anomalies = db.query(QualityAnomaly).filter(QualityAnomaly.status == "open").count()
    total_anomalies = db.query(QualityAnomaly).count() or 1
    anomaly_percent = round(open_anomalies / total_anomalies * 100)

    # severity distribution as segments
    sev_rows = (
        db.query(QualityAnomaly.severity, func.count(QualityAnomaly.id))
        .group_by(QualityAnomaly.severity)
        .all()
    )
    anomaly_segments = [
        AnomalySegment(name=sev or "其他", value=cnt) for sev, cnt in sev_rows
    ] or [AnomalySegment(name="正常", value=1)]

    production_trend = efficiency_trend[-8:] if len(efficiency_trend) >= 8 else efficiency_trend

    # hourly bars for today
    hourly_bars = []
    hourly_output_trend = []
    for h in range(8, 20):
        start = datetime.combine(today, datetime.min.time()).replace(hour=h)
        end = start + timedelta(hours=1)
        qty = int(
            db.query(func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0))
            .filter(
                ProductionOutputRecord.record_at >= start,
                ProductionOutputRecord.record_at < end,
            )
            .scalar()
            or 0
        )
        hourly_bars.append(qty)
        if h % 2 == 0:
            hourly_output_trend.append(qty)

    completed_today = daily_current
    efficiency_rate = round(daily_current / daily_target * 100) if daily_target else 0

    return ManufacturingDashboard(
        display_date=today.strftime("%Y.%m.%d"),
        monthly_output=monthly_output,
        last_month_output=last_month_output,
        daily_current=daily_current,
        daily_target=daily_target,
        efficiency_count=completed_today,
        efficiency_rate=min(efficiency_rate, 100),
        efficiency_trend=efficiency_trend,
        anomaly_percent=anomaly_percent,
        anomaly_segments=anomaly_segments,
        production_trend_value=float(production_trend[-1] if production_trend else 0),
        production_trend=production_trend,
        hourly_avg=round(sum(hourly_bars) / max(len(hourly_bars), 1), 2),
        hourly_bars=hourly_bars or [0] * 12,
        hourly_output_trend=hourly_output_trend or [0],
        hourly_stats=HourlyStats(
            production_time=datetime.now().strftime("%H:%M"),
            daily_output=daily_current,
            daily_avg=int(sum(efficiency_trend[-7:]) / 7) if efficiency_trend else 0,
        ),
    )


def _dashboard(db: Session) -> DashboardResponse:
    today = date.today()
    pending = db.query(WorkOrder).filter(WorkOrder.status == "pending").count()
    today_output = int(
        db.query(func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0))
        .filter(ProductionOutputRecord.record_at >= datetime.combine(today, datetime.min.time()))
        .scalar()
        or 0
    )
    active_exceptions = (
        db.query(QualityAnomaly).filter(QualityAnomaly.status == "open").count()
    )
    month_start = today.replace(day=1)
    month_plan = int(
        db.query(func.coalesce(func.sum(ProductionPlan.plan_qty), 0))
        .filter(ProductionPlan.plan_date >= month_start)
        .scalar()
        or 0
    )
    month_actual = int(
        db.query(func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0))
        .filter(
            ProductionOutputRecord.record_at
            >= datetime.combine(month_start, datetime.min.time())
        )
        .scalar()
        or 0
    )
    monthly_completion = round(month_actual / month_plan * 100, 1) if month_plan else 0

    stats = [
        DashboardStatItem(
            key="pending_orders",
            label="待处理工单",
            value=pending,
            unit="个",
            trend="",
        ),
        DashboardStatItem(
            key="today_output",
            label="今日产量",
            value=today_output,
            unit="件",
            trend="",
        ),
        DashboardStatItem(
            key="active_exceptions",
            label="活跃异常",
            value=active_exceptions,
            unit="项",
            trend="",
        ),
        DashboardStatItem(
            key="monthly_completion",
            label="本月完成率",
            value=monthly_completion,
            unit="%",
            trend="",
        ),
    ]

    production_trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        qty = int(
            db.query(func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0))
            .filter(
                ProductionOutputRecord.record_at >= datetime.combine(d, datetime.min.time()),
                ProductionOutputRecord.record_at
                < datetime.combine(d + timedelta(days=1), datetime.min.time()),
            )
            .scalar()
            or 0
        )
        production_trend.append(ProductionTrendPoint(date=d.strftime("%m-%d"), output=qty))

    status_rows = (
        db.query(WorkOrder.status, func.count(WorkOrder.id)).group_by(WorkOrder.status).all()
    )
    work_order_status = [
        WorkOrderStatusItem(status=STATUS_LABEL.get(s, s), count=c) for s, c in status_rows
    ]

    todos = (
        db.query(DashboardTodo)
        .filter(DashboardTodo.status == "open")
        .order_by(DashboardTodo.id)
        .limit(10)
        .all()
    )
    todo_items = [
        TodoItem(
            id=t.id,
            type=t.type,
            title=t.title,
            description=t.description or "",
            priority=t.priority,
            link=t.link or "",
        )
        for t in todos
    ]

    return DashboardResponse(
        stats=stats,
        production_trend=production_trend,
        work_order_status=work_order_status,
        todos=todo_items,
        manufacturing=_manufacturing(db),
    )


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _dashboard(db)


_OVERDUE_EXCLUDED = ("completed", "cancelled")


def _workbench_cards(db: Session) -> list[WorkbenchCard]:
    today = date.today()
    overdue = (
        db.query(WorkOrder)
        .filter(
            WorkOrder.end_date.isnot(None),
            WorkOrder.end_date < today,
            WorkOrder.status.notin_(_OVERDUE_EXCLUDED),
        )
        .count()
    )
    unread = db.query(Message).filter(Message.is_read.is_(False)).count()
    open_anomalies = (
        db.query(QualityAnomaly).filter(QualityAnomaly.status == "open").count()
    )
    low_stock = (
        db.query(InventoryStock)
        .filter(
            InventoryStock.safety_stock > 0,
            InventoryStock.quantity < InventoryStock.safety_stock,
        )
        .count()
    )
    return [
        WorkbenchCard(
            key="overdue_work_orders",
            label="逾期工单",
            value=overdue,
            unit="单",
            link="/work-orders/overdue",
        ),
        WorkbenchCard(
            key="unread_messages",
            label="未读消息",
            value=unread,
            unit="条",
            link="/messages",
        ),
        WorkbenchCard(
            key="open_quality_anomalies",
            label="品质异常",
            value=open_anomalies,
            unit="项",
            link="/quality-management/anomalies",
        ),
        WorkbenchCard(
            key="low_stock_alerts",
            label="低库存预警",
            value=low_stock,
            unit="项",
            link="/warehouse/low-stock",
        ),
    ]


@router.get(
    "/workbench",
    response_model=WorkbenchResponse,
    summary="工作台汇总",
    description=(
        "四张业务数字卡（逾期工单 / 未读消息 / 品质异常 / 低库存）+ 待办列表；"
        "待办默认仅 open，可用 todo_type 筛选。"
    ),
)
def get_workbench(
    todo_type: str | None = Query(None, description="待办类型筛选"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(DashboardTodo).filter(DashboardTodo.status == "open")
    if todo_type:
        query = query.filter(DashboardTodo.type == todo_type.strip())
    todos = query.order_by(DashboardTodo.id.desc()).limit(50).all()
    return WorkbenchResponse(
        cards=_workbench_cards(db),
        todos=[
            WorkbenchTodoItem(
                id=t.id,
                type=t.type,
                title=t.title,
                description=t.description or "",
                priority=t.priority,
                link=t.link or "",
                status=t.status,
                created_at=t.created_at,
            )
            for t in todos
        ],
    )


@router.patch(
    "/todos/{todo_id}/complete",
    response_model=WorkbenchTodoItem,
    summary="完成工作台待办",
    description="将待办标记为 done；已完成则幂等返回。",
)
def complete_dashboard_todo(
    todo_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = db.query(DashboardTodo).filter(DashboardTodo.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="待办不存在")
    if todo.status != "done":
        todo.status = "done"
        db.commit()
        db.refresh(todo)
    return WorkbenchTodoItem(
        id=todo.id,
        type=todo.type,
        title=todo.title,
        description=todo.description or "",
        priority=todo.priority,
        link=todo.link or "",
        status=todo.status,
        created_at=todo.created_at,
    )
