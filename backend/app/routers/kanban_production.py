"""生产看板 — 从产量事实表聚合。"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Product, ProductionOutputRecord, ProductionPlan, User
from app.schemas import (
    CompletionChartPoint,
    ProductionDetailRow,
    ProductionKanbanDashboard,
    ProductionStatsRow,
)

router = APIRouter(prefix="/api/kanban", tags=["kanban-production"])

WEEKDAY_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def _build_production_kanban(db: Session) -> ProductionKanbanDashboard:
    today = date.today()
    now = datetime.now()
    start = datetime.combine(today, datetime.min.time())

    outputs = (
        db.query(ProductionOutputRecord)
        .filter(ProductionOutputRecord.record_at >= start)
        .order_by(ProductionOutputRecord.record_at)
        .all()
    )

    # cumulative stats by hour
    by_hour: dict[int, dict] = defaultdict(
        lambda: {
            "completed": 0,
            "area": 0.0,
            "defect": 0,
            "incoming": 0,
        }
    )
    for o in outputs:
        h = o.record_at.hour
        by_hour[h]["completed"] += o.actual_qty
        by_hour[h]["area"] += float(o.area_output or 0)
        by_hour[h]["defect"] += o.defect_qty
        by_hour[h]["incoming"] += o.incoming_boards

    stats_rows = []
    cum = {"completed": 0, "area": 0.0, "defect": 0, "incoming": 0}
    for h in sorted(by_hour.keys()):
        cum["completed"] += by_hour[h]["completed"]
        cum["area"] += by_hour[h]["area"]
        cum["defect"] += by_hour[h]["defect"]
        cum["incoming"] += by_hour[h]["incoming"]
        rate = (
            f"{round(cum['defect'] / cum['completed'] * 100, 2)}%"
            if cum["completed"]
            else "0%"
        )
        stats_rows.append(
            ProductionStatsRow(
                time=f"{h:02d}:00",
                today_completed=cum["completed"],
                today_area_output=round(cum["area"], 1),
                today_defect_total=cum["defect"],
                daily_defect_rate=rate,
                today_incoming_boards=cum["incoming"],
            )
        )
    if not stats_rows:
        stats_rows = [
            ProductionStatsRow(
                time="08:00",
                today_completed=0,
                today_area_output=0,
                today_defect_total=0,
                daily_defect_rate="0%",
                today_incoming_boards=0,
            )
        ]

    chart = []
    for row in stats_rows:
        chart.append(
            CompletionChartPoint(
                label=row.time,
                lot_output=row.today_completed,
                model_output=row.today_completed,
            )
        )

    detail_rows = []
    for o in outputs[-30:]:
        product = (
            db.query(Product).filter(Product.id == o.product_id).first()
            if o.product_id
            else None
        )
        detail_rows.append(
            ProductionDetailRow(
                time=o.record_at.strftime("%H:%M:%S"),
                process_card_no=o.process_card_no or "-",
                product_model=(product.model or product.product_code) if product else "-",
                quantity=o.actual_qty,
                today_completed=o.actual_qty,
                total_completed=o.actual_qty,
            )
        )

    plan_today = sum(
        p.plan_qty for p in db.query(ProductionPlan).filter(ProductionPlan.plan_date == today)
    )
    actual_today = sum(o.actual_qty for o in outputs)
    achievement = round(actual_today / plan_today * 100, 1) if plan_today else 0
    area_kpi = round(sum(float(o.area_output or 0) for o in outputs) / 1000, 1)

    return ProductionKanbanDashboard(
        board_category="production",
        display_time=now.strftime("%Y-%m-%d %H:%M:%S"),
        weekday=WEEKDAY_CN[now.weekday()],
        achievement_rate=achievement,
        production_area=area_kpi,
        stats_rows=stats_rows,
        detail_rows=detail_rows,
        completion_chart=chart,
    )


@router.get("/production", response_model=ProductionKanbanDashboard)
def get_production_kanban(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _refresh: int | None = Query(None),
):
    return _build_production_kanban(db)
