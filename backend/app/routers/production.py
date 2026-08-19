"""生产总览 API — 从生产计划 / 产量 / WIP / 工单等表聚合。"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    LineCapacitySnapshot,
    Product,
    ProductionLine,
    ProductionOutputRecord,
    ProductionPlan,
    QualityDefectDetail,
    QualityMetrics,
    User,
    WipSnapshot,
    WorkOrder,
)
from app.schemas import (
    CompletionChartPoint,
    ProductionDetailRow,
    ProductionOverviewResponse,
    ProductionOverviewStats,
    ProductionStatTrend,
)
from app.seed_analytics import PRODUCTION_LINE_NAMES, WIP_STATUSES

router = APIRouter(prefix="/api/production", tags=["production"])

STATUS_MAP = {
    "pending": "待开工",
    "in_progress": "进行中",
    "completed": "完成",
    "closed": "完成",
}


def _line_filter(db: Session, line: str) -> list[ProductionLine]:
    q = db.query(ProductionLine).filter(ProductionLine.is_active.is_(True))
    if line and line != "全部":
        q = q.filter(ProductionLine.name == line)
    return q.order_by(ProductionLine.id).all()


def _period_bounds(period: str) -> tuple[datetime, datetime, list[str]]:
    now = datetime.utcnow()
    today = now.date()
    if period == "day":
        start = datetime.combine(today, datetime.min.time())
        labels = ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00"]
        return start, now, labels
    if period == "week":
        start = datetime.combine(today - timedelta(days=6), datetime.min.time())
        labels = [(today - timedelta(days=i)).strftime("%m-%d") for i in range(6, -1, -1)]
        return start, now, labels
    start = datetime.combine(today - timedelta(days=27), datetime.min.time())
    labels = ["第1周", "第2周", "第3周", "第4周"]
    return start, now, labels


def _trend_bucket(record_at: datetime, period: str, labels: list[str]) -> str | None:
    if period == "day":
        hour = record_at.hour
        for label in labels:
            h = int(label.split(":")[0])
            if hour <= h:
                return label
        return labels[-1] if labels else None
    if period == "week":
        key = record_at.strftime("%m-%d")
        return key if key in labels else None
    # month → 4 weeks
    today = date.today()
    day_offset = (today - record_at.date()).days
    if day_offset < 0:
        return None
    week_idx = min(3, day_offset // 7)
    # labels are 第1周..第4周 from oldest to newest
    idx = 3 - week_idx
    return labels[idx] if 0 <= idx < len(labels) else None


def _build_overview_v2(db: Session, period: str, line: str) -> dict:
    lines = _line_filter(db, line)
    line_ids = [ln.id for ln in lines]
    line_names = [ln.name for ln in lines] or PRODUCTION_LINE_NAMES
    start, end, labels = _period_bounds(period)

    plan_q = db.query(ProductionPlan).filter(
        ProductionPlan.plan_date >= start.date(),
        ProductionPlan.plan_date <= end.date(),
    )
    out_q = db.query(ProductionOutputRecord).filter(
        ProductionOutputRecord.record_at >= start,
        ProductionOutputRecord.record_at <= end,
    )
    if line_ids:
        plan_q = plan_q.filter(ProductionPlan.production_line_id.in_(line_ids))
        out_q = out_q.filter(ProductionOutputRecord.production_line_id.in_(line_ids))

    plans = plan_q.all()
    outputs = out_q.all()

    # --- achievement comparison ---
    if line == "全部":
        plan_by_line: dict[int, int] = defaultdict(int)
        actual_by_line: dict[int, int] = defaultdict(int)
        for p in plans:
            plan_by_line[p.production_line_id] += p.plan_qty
        for o in outputs:
            actual_by_line[o.production_line_id] += o.actual_qty
        comparison = []
        for ln in lines:
            plan_qty = plan_by_line.get(ln.id, 0)
            actual_qty = actual_by_line.get(ln.id, 0)
            comparison.append(
                {
                    "name": ln.name,
                    "plan_quantity": plan_qty,
                    "actual_quantity": actual_qty,
                    "achievement_rate": round(actual_qty / plan_qty * 100, 1) if plan_qty else 0,
                }
            )
    else:
        plan_by_product: dict[int, int] = defaultdict(int)
        actual_by_product: dict[int, int] = defaultdict(int)
        for p in plans:
            plan_by_product[p.product_id] += p.plan_qty
        for o in outputs:
            if o.product_id:
                actual_by_product[o.product_id] += o.actual_qty
        product_ids = set(plan_by_product) | set(actual_by_product)
        products = {
            p.id: p
            for p in db.query(Product).filter(Product.id.in_(product_ids)).all()
        } if product_ids else {}
        comparison = []
        for pid in sorted(product_ids):
            prod = products.get(pid)
            plan_qty = plan_by_product.get(pid, 0)
            actual_qty = actual_by_product.get(pid, 0)
            comparison.append(
                {
                    "name": prod.product_code if prod else f"P-{pid}",
                    "plan_quantity": plan_qty,
                    "actual_quantity": actual_qty,
                    "achievement_rate": round(actual_qty / plan_qty * 100, 1) if plan_qty else 0,
                }
            )

    plan_quantity = sum(i["plan_quantity"] for i in comparison)
    actual_quantity = sum(i["actual_quantity"] for i in comparison)
    achievement_rate = round(actual_quantity / plan_quantity * 100, 1) if plan_quantity else 0

    # --- output trend ---
    plan_buckets: dict[str, int] = {lb: 0 for lb in labels}
    actual_buckets: dict[str, int] = {lb: 0 for lb in labels}
    if period == "day":
        # distribute daily plan evenly across labels
        day_plan = sum(
            p.plan_qty
            for p in plans
            if p.plan_date == end.date()
        )
        share = day_plan // max(len(labels), 1)
        for lb in labels:
            plan_buckets[lb] = share
    elif period == "week":
        for p in plans:
            key = p.plan_date.strftime("%m-%d")
            if key in plan_buckets:
                plan_buckets[key] += p.plan_qty
    else:
        for p in plans:
            day_offset = (end.date() - p.plan_date).days
            if 0 <= day_offset <= 27:
                idx = 3 - min(3, day_offset // 7)
                plan_buckets[labels[idx]] += p.plan_qty

    for o in outputs:
        bucket = _trend_bucket(o.record_at, period, labels)
        if bucket:
            actual_buckets[bucket] += o.actual_qty

    trend = {
        "granularity": "day" if period == "month" else period,
        "labels": labels,
        "plan": [plan_buckets[lb] for lb in labels],
        "actual": [actual_buckets[lb] for lb in labels],
    }

    # --- work order status ---
    wo_q = db.query(WorkOrder.status, func.count(WorkOrder.id)).group_by(WorkOrder.status)
    if line != "全部":
        wo_q = wo_q.filter(WorkOrder.production_line == line)
    wo_counts = {STATUS_MAP.get(s, s): c for s, c in wo_q.all()}
    work_order_status = [
        {"status": "待开工", "count": wo_counts.get("待开工", 0)},
        {"status": "进行中", "count": wo_counts.get("进行中", 0)},
        {"status": "完成", "count": wo_counts.get("完成", 0)},
    ]

    # --- WIP ---
    latest_wip_at = db.query(func.max(WipSnapshot.snapshot_at)).scalar()
    wip_rows_raw = []
    if latest_wip_at:
        wip_q = db.query(WipSnapshot).filter(WipSnapshot.snapshot_at == latest_wip_at)
        if line_ids:
            wip_q = wip_q.filter(WipSnapshot.production_line_id.in_(line_ids))
        wip_rows_raw = wip_q.all()

    if line == "全部":
        by_line: dict[int, dict[str, int]] = defaultdict(lambda: {s: 0 for s in WIP_STATUSES})
        for row in wip_rows_raw:
            by_line[row.production_line_id][row.status] = row.quantity
        wip = {
            "statuses": WIP_STATUSES,
            "rows": [
                {
                    "name": ln.name,
                    "values": [by_line[ln.id].get(s, 0) for s in WIP_STATUSES],
                }
                for ln in lines
            ],
        }
    else:
        by_product: dict[str, dict[str, int]] = defaultdict(lambda: {s: 0 for s in WIP_STATUSES})
        product_map = {
            p.id: p.product_code
            for p in db.query(Product).filter(Product.default_line_id.in_(line_ids)).all()
        } if line_ids else {}
        for row in wip_rows_raw:
            name = product_map.get(row.product_id, "未指定") if row.product_id else "未指定"
            by_product[name][row.status] += row.quantity
        wip = {
            "statuses": WIP_STATUSES,
            "rows": [
                {"name": name, "values": [vals.get(s, 0) for s in WIP_STATUSES]}
                for name, vals in by_product.items()
            ],
        }

    # --- line load ---
    latest_cap_at = db.query(func.max(LineCapacitySnapshot.snapshot_at)).scalar()
    line_load = []
    if latest_cap_at:
        cap_q = db.query(LineCapacitySnapshot).filter(
            LineCapacitySnapshot.snapshot_at == latest_cap_at
        )
        if line_ids:
            cap_q = cap_q.filter(LineCapacitySnapshot.production_line_id.in_(line_ids))
        caps = cap_q.all()
        if line == "全部":
            # one row per line (station_name is null or aggregate)
            by_ln: dict[int, LineCapacitySnapshot] = {}
            for c in caps:
                if c.station_name is None or c.production_line_id not in by_ln:
                    by_ln[c.production_line_id] = c
            for ln in lines:
                c = by_ln.get(ln.id)
                line_load.append(
                    {
                        "name": ln.name,
                        "load_rate": float(c.load_rate) if c else 0,
                        "capacity_utilization": float(c.capacity_utilization) if c else 0,
                    }
                )
        else:
            for c in caps:
                if c.station_name:
                    line_load.append(
                        {
                            "name": c.station_name,
                            "load_rate": float(c.load_rate),
                            "capacity_utilization": float(c.capacity_utilization),
                        }
                    )
            if not line_load:
                for ln in lines:
                    for c in caps:
                        if c.production_line_id == ln.id:
                            line_load.append(
                                {
                                    "name": ln.name,
                                    "load_rate": float(c.load_rate),
                                    "capacity_utilization": float(c.capacity_utilization),
                                }
                            )

    # --- quality from quality_metrics ---
    qm = db.query(QualityMetrics).filter(
        QualityMetrics.record_date >= start.date(),
        QualityMetrics.record_date <= end.date(),
    )
    if line != "全部":
        qm = qm.filter(QualityMetrics.production_line == line)
    metrics = qm.all()
    inspected = sum(m.total_inspected for m in metrics) or 1
    defects = sum(m.defect_count for m in metrics)
    defect_rate = round(defects / inspected * 100, 2)

    defect_trend_map: dict[str, list[float]] = defaultdict(list)
    for m in metrics:
        if period == "day":
            # approximate by date only — use single day average per label evenly
            key = labels[min(len(labels) - 1, 0)]
        elif period == "week":
            key = m.record_date.strftime("%m-%d")
        else:
            day_offset = (end.date() - m.record_date).days
            idx = 3 - min(3, max(0, day_offset) // 7)
            key = labels[idx]
        if m.total_inspected:
            defect_trend_map[key].append(m.defect_count / m.total_inspected * 100)

    defect_rate_trend = []
    for lb in labels:
        vals = defect_trend_map.get(lb) or []
        defect_rate_trend.append(
            {"label": lb, "value": round(sum(vals) / len(vals), 2) if vals else defect_rate}
        )

    defect_q = db.query(
        QualityDefectDetail.defect_type,
        func.sum(QualityDefectDetail.quantity),
    ).group_by(QualityDefectDetail.defect_type)
    if line != "全部":
        defect_q = defect_q.filter(QualityDefectDetail.production_line == line)
    distribution = [
        {"name": name or "其他", "value": int(qty or 0)}
        for name, qty in defect_q.all()
    ] or [{"name": "其他", "value": defects or 1}]

    quality = {
        "defect_rate": defect_rate,
        "defect_rate_trend": defect_rate_trend,
        "defect_distribution": distribution,
    }

    # --- equipment / line utilization from capacity ---
    equipment = []
    for item in line_load:
        equipment.append(
            {
                "name": item["name"],
                "line_name": line if line != "全部" else item["name"],
                "utilization": item["load_rate"],
                "oee": round(item["capacity_utilization"] * 0.82, 1),
            }
        )

    today = date.today()
    week_start = today - timedelta(days=6)
    today_output = (
        db.query(func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0))
        .filter(
            ProductionOutputRecord.record_at >= datetime.combine(today, datetime.min.time()),
            *([ProductionOutputRecord.production_line_id.in_(line_ids)] if line_ids else []),
        )
        .scalar()
    )
    week_output = (
        db.query(func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0))
        .filter(
            ProductionOutputRecord.record_at
            >= datetime.combine(week_start, datetime.min.time()),
            *([ProductionOutputRecord.production_line_id.in_(line_ids)] if line_ids else []),
        )
        .scalar()
    )

    wo_base = db.query(WorkOrder)
    if line != "全部":
        wo_base = wo_base.filter(WorkOrder.production_line == line)
    in_progress_orders = wo_base.filter(WorkOrder.status == "in_progress").count()
    completed_orders = wo_base.filter(WorkOrder.status.in_(["completed", "closed"])).count()
    pending_orders = wo_base.filter(WorkOrder.status == "pending").count()

    plan_output = sum(trend["plan"]) or 1
    actual_output = sum(trend["actual"])
    completion_rate = round(actual_output / plan_output * 100, 1)
    wip_total = sum(sum(row["values"]) for row in wip["rows"])
    avg_line_load = (
        round(sum(item["load_rate"] for item in line_load) / len(line_load), 1)
        if line_load
        else 0
    )

    all_line_names = [ln.name for ln in db.query(ProductionLine).order_by(ProductionLine.id).all()]
    if not all_line_names:
        all_line_names = PRODUCTION_LINE_NAMES

    return {
        "period": period,
        "production_line": line,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lines": all_line_names,
        "kpi": {
            "achievement_rate": achievement_rate,
            "plan_quantity": plan_quantity,
            "actual_quantity": actual_quantity,
            "achievement_diff": actual_quantity - plan_quantity,
            "today_output": int(today_output or 0),
            "week_output": int(week_output or 0),
            "in_progress_orders": in_progress_orders,
            "completed_orders": completed_orders,
            "pending_orders": pending_orders,
            "completion_rate": completion_rate,
            "completion_rate_trend": "",
            "wip_total": wip_total,
            "wip_total_trend": "",
            "avg_line_load": avg_line_load,
            "avg_line_load_trend": "",
            "plan_achievement_rate": achievement_rate,
            "plan_achievement_rate_trend": "",
        },
        "achievement_comparison": comparison,
        "output_trend": trend,
        "work_order_status": work_order_status,
        "line_load": line_load,
        "wip_overview": wip,
        "quality": quality,
        "equipment": equipment,
    }


def _build_overview_v1(db: Session) -> ProductionOverviewResponse:
    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    outputs = (
        db.query(ProductionOutputRecord)
        .filter(ProductionOutputRecord.record_at >= start)
        .order_by(ProductionOutputRecord.record_at)
        .all()
    )
    completed = sum(o.actual_qty for o in outputs)
    area = float(sum(float(o.area_output or 0) for o in outputs))
    defects = sum(o.defect_qty for o in outputs)
    incoming = sum(o.incoming_boards for o in outputs)
    rate = f"{round(defects / completed * 100, 2)}%" if completed else "0%"

    # hourly completion chart
    by_hour: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for o in outputs:
        label = f"{o.record_at.hour:02d}:00"
        by_hour[label][0] += o.actual_qty
        by_hour[label][1] += o.actual_qty
    chart = [
        CompletionChartPoint(label=k, lot_output=v[0], model_output=v[1])
        for k, v in sorted(by_hour.items())
    ] or [
        CompletionChartPoint(label="08:00", lot_output=0, model_output=0),
    ]

    detail_rows = []
    for o in outputs[-20:]:
        product = db.query(Product).filter(Product.id == o.product_id).first() if o.product_id else None
        detail_rows.append(
            ProductionDetailRow(
                time=o.record_at.strftime("%H:%M:%S"),
                process_card_no=o.process_card_no or "-",
                product_model=product.model or product.product_code if product else "-",
                quantity=o.actual_qty,
                today_completed=o.actual_qty,
                total_completed=o.actual_qty,
            )
        )

    plan_today = (
        db.query(func.coalesce(func.sum(ProductionPlan.plan_qty), 0))
        .filter(ProductionPlan.plan_date == today)
        .scalar()
    )
    achievement = round(completed / plan_today * 100, 1) if plan_today else 0

    return ProductionOverviewResponse(
        achievement_rate=achievement,
        production_area=round(area / 1000, 1) if area else 0,
        kpi_trends={
            "achievement_rate": ProductionStatTrend(direction="up", text=""),
            "production_area": ProductionStatTrend(direction="up", text=""),
        },
        stats=ProductionOverviewStats(
            today_completed=completed,
            today_area_output=round(area, 1),
            today_defect_total=defects,
            daily_defect_rate=rate,
            today_incoming_boards=incoming,
            trends={},
        ),
        completion_chart=chart,
        detail_rows=detail_rows,
    )


@router.get("/overview", response_model=ProductionOverviewResponse)
def get_production_overview(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _build_overview_v1(db)


@router.get("/overview-v2")
def get_production_overview_v2(
    period: str = Query("day", pattern=r"^(day|week|month)$"),
    line: str = Query("全部"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _build_overview_v2(db, period, line)
