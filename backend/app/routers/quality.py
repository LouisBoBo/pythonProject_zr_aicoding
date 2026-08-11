from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import QualityAnomaly, QualityDefectDetail, QualityMetrics, User
from app.schemas import (
    QualityAnomalyItem,
    QualityAnomalyListResponse,
    QualityDefectDistributionItem,
    QualityDefectDistributionResponse,
    QualityKpiItem,
    QualityKpiResponse,
    QualityProcessYieldItem,
    QualityProcessYieldResponse,
    QualityTopDefectItem,
    QualityTopDefectResponse,
    QualityTrendPoint,
    QualityTrendResponse,
)

router = APIRouter(prefix="/api/quality", tags=["quality"])

LINES = ["SMT-1线", "SMT-2线", "DIP线", "组装线", "测试线"]
PROCESSES = ["贴片", "焊接", "AOI检测", "功能测试", "包装"]
DEFECT_TYPES = ["虚焊", "短路", "元件偏移", "漏件", "外观不良", "功能异常", "尺寸偏差"]


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator * 100, 2)


def _period_bounds(period: str) -> tuple[date, date, date, date]:
    today = date.today()
    if period == "week":
        start = today - timedelta(days=today.weekday())
        prev_start = start - timedelta(days=7)
        prev_end = start - timedelta(days=1)
        return start, today, prev_start, prev_end
    if period == "month":
        start = today.replace(day=1)
        prev_end = start - timedelta(days=1)
        prev_start = prev_end.replace(day=1)
        return start, today, prev_start, prev_end
    prev = today - timedelta(days=1)
    return today, today, prev, prev


def _aggregate_metrics(db: Session, start: date, end: date) -> dict:
    row = (
        db.query(
            func.coalesce(func.sum(QualityMetrics.good_count), 0),
            func.coalesce(func.sum(QualityMetrics.defect_count), 0),
            func.coalesce(func.sum(QualityMetrics.scrap_count), 0),
            func.coalesce(func.sum(QualityMetrics.total_inspected), 0),
        )
        .filter(QualityMetrics.record_date >= start, QualityMetrics.record_date <= end)
        .one()
    )
    good, defect, scrap, total = row
    return {
        "good": int(good),
        "defect": int(defect),
        "scrap": int(scrap),
        "total": int(total),
    }


def _change_direction(current: float, previous: float, higher_is_better: bool) -> tuple[float | None, str | None]:
    if previous == 0:
        return None, None
    delta = round(current - previous, 2)
    if delta == 0:
        return 0.0, "flat"
    improved = delta > 0 if higher_is_better else delta < 0
    return abs(delta), "up" if improved else "down"


@router.get("/kpi", response_model=QualityKpiResponse)
def get_quality_kpi(
    period: str = Query("day", pattern="^(day|week|month)$"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    start, end, prev_start, prev_end = _period_bounds(period)
    current = _aggregate_metrics(db, start, end)
    previous = _aggregate_metrics(db, prev_start, prev_end)

    yield_rate = _safe_rate(current["good"], current["total"])
    prev_yield = _safe_rate(previous["good"], previous["total"])
    defect_rate = _safe_rate(current["defect"], current["total"])
    prev_defect = _safe_rate(previous["defect"], previous["total"])
    scrap_rate = _safe_rate(current["scrap"], current["total"])
    prev_scrap = _safe_rate(previous["scrap"], previous["total"])

    first_pass = _safe_rate(current["good"], current["good"] + current["defect"])
    prev_first_pass = _safe_rate(previous["good"], previous["good"] + previous["defect"])

    open_count = (
        db.query(func.count(QualityAnomaly.id))
        .filter(QualityAnomaly.status == "open")
        .scalar()
        or 0
    )
    prev_open_count = (
        db.query(func.count(QualityAnomaly.id))
        .filter(
            QualityAnomaly.status == "open",
            QualityAnomaly.discovered_at >= datetime.combine(prev_start, datetime.min.time()),
            QualityAnomaly.discovered_at <= datetime.combine(prev_end, datetime.max.time()),
        )
        .scalar()
        or 0
    )

    yield_change, yield_dir = _change_direction(yield_rate, prev_yield, True)
    defect_change, defect_dir = _change_direction(defect_rate, prev_defect, False)
    scrap_change, scrap_dir = _change_direction(scrap_rate, prev_scrap, False)
    fpy_change, fpy_dir = _change_direction(first_pass, prev_first_pass, True)
    open_change = float(open_count - prev_open_count)
    open_dir = "down" if open_change < 0 else ("up" if open_change > 0 else "flat")

    return QualityKpiResponse(
        period=period,
        items=[
            QualityKpiItem(key="yield_rate", label="良率", value=yield_rate, change=yield_change, change_direction=yield_dir),
            QualityKpiItem(key="defect_rate", label="不良率", value=defect_rate, change=defect_change, change_direction=defect_dir),
            QualityKpiItem(key="scrap_rate", label="报废率", value=scrap_rate, change=scrap_change, change_direction=scrap_dir),
            QualityKpiItem(key="first_pass_yield", label="一次合格率", value=first_pass, change=fpy_change, change_direction=fpy_dir),
            QualityKpiItem(
                key="open_anomalies",
                label="待处理异常",
                value=float(open_count),
                unit="件",
                change=abs(open_change) if open_change else 0.0,
                change_direction=open_dir if open_change != 0 else "flat",
            ),
        ],
    )


@router.get("/trend", response_model=QualityTrendResponse)
def get_quality_trend(
    granularity: str = Query("day", pattern="^(day|week|month)$"),
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    today = date.today()
    start = today - timedelta(days=days - 1)
    rows = (
        db.query(
            QualityMetrics.record_date,
            func.sum(QualityMetrics.good_count),
            func.sum(QualityMetrics.defect_count),
            func.sum(QualityMetrics.total_inspected),
        )
        .filter(QualityMetrics.record_date >= start, QualityMetrics.record_date <= today)
        .group_by(QualityMetrics.record_date)
        .order_by(QualityMetrics.record_date)
        .all()
    )
    daily_map = {
        r[0]: {"good": int(r[1] or 0), "defect": int(r[2] or 0), "total": int(r[3] or 0)}
        for r in rows
    }

    points: list[QualityTrendPoint] = []
    if granularity == "day":
        cursor = start
        while cursor <= today:
            data = daily_map.get(cursor, {"good": 0, "defect": 0, "total": 0})
            points.append(
                QualityTrendPoint(
                    label=cursor.strftime("%m-%d"),
                    yield_rate=_safe_rate(data["good"], data["total"]),
                    defect_rate=_safe_rate(data["defect"], data["total"]),
                )
            )
            cursor += timedelta(days=1)
    elif granularity == "week":
        week_start = start - timedelta(days=start.weekday())
        while week_start <= today:
            week_end = min(week_start + timedelta(days=6), today)
            good = defect = total = 0
            d = week_start
            while d <= week_end:
                if d in daily_map:
                    good += daily_map[d]["good"]
                    defect += daily_map[d]["defect"]
                    total += daily_map[d]["total"]
                d += timedelta(days=1)
            points.append(
                QualityTrendPoint(
                    label=f"{week_start.strftime('%m-%d')}~{week_end.strftime('%m-%d')}",
                    yield_rate=_safe_rate(good, total),
                    defect_rate=_safe_rate(defect, total),
                )
            )
            week_start += timedelta(days=7)
    else:
        cursor = start.replace(day=1)
        while cursor <= today:
            if cursor.month == 12:
                month_end = date(cursor.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(cursor.year, cursor.month + 1, 1) - timedelta(days=1)
            month_end = min(month_end, today)
            good = defect = total = 0
            d = cursor
            while d <= month_end:
                if d in daily_map:
                    good += daily_map[d]["good"]
                    defect += daily_map[d]["defect"]
                    total += daily_map[d]["total"]
                d += timedelta(days=1)
            points.append(
                QualityTrendPoint(
                    label=cursor.strftime("%Y-%m"),
                    yield_rate=_safe_rate(good, total),
                    defect_rate=_safe_rate(defect, total),
                )
            )
            if cursor.month == 12:
                cursor = date(cursor.year + 1, 1, 1)
            else:
                cursor = date(cursor.year, cursor.month + 1, 1)

    return QualityTrendResponse(granularity=granularity, points=points)


@router.get("/process-yield", response_model=QualityProcessYieldResponse)
def get_process_yield(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    today = date.today()
    start = today - timedelta(days=6)
    rows = (
        db.query(
            QualityMetrics.process,
            func.sum(QualityMetrics.good_count),
            func.sum(QualityMetrics.total_inspected),
        )
        .filter(QualityMetrics.record_date >= start, QualityMetrics.record_date <= today)
        .group_by(QualityMetrics.process)
        .all()
    )
    process_order = {p: i for i, p in enumerate(PROCESSES)}
    items = [
        QualityProcessYieldItem(
            process=row[0],
            yield_rate=_safe_rate(int(row[1] or 0), int(row[2] or 0)),
            total_inspected=int(row[2] or 0),
        )
        for row in rows
    ]
    items.sort(key=lambda x: process_order.get(x.process, 99))
    return QualityProcessYieldResponse(items=items)


@router.get("/defect-distribution", response_model=QualityDefectDistributionResponse)
def get_defect_distribution(
    by: str = Query("type", pattern="^(type|line|process)$"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if by == "type":
        rows = (
            db.query(QualityDefectDetail.defect_type, func.sum(QualityDefectDetail.quantity))
            .group_by(QualityDefectDetail.defect_type)
            .order_by(func.sum(QualityDefectDetail.quantity).desc())
            .all()
        )
        items = [QualityDefectDistributionItem(name=r[0], value=int(r[1] or 0)) for r in rows]
    elif by == "line":
        rows = (
            db.query(QualityDefectDetail.production_line, func.sum(QualityDefectDetail.quantity))
            .filter(QualityDefectDetail.production_line.isnot(None))
            .group_by(QualityDefectDetail.production_line)
            .order_by(func.sum(QualityDefectDetail.quantity).desc())
            .all()
        )
        items = [QualityDefectDistributionItem(name=r[0] or "未知", value=int(r[1] or 0)) for r in rows]
    else:
        rows = (
            db.query(QualityDefectDetail.process, func.sum(QualityDefectDetail.quantity))
            .filter(QualityDefectDetail.process.isnot(None))
            .group_by(QualityDefectDetail.process)
            .order_by(func.sum(QualityDefectDetail.quantity).desc())
            .all()
        )
        items = [QualityDefectDistributionItem(name=r[0] or "未知", value=int(r[1] or 0)) for r in rows]

    return QualityDefectDistributionResponse(by=by, items=items)


@router.get("/anomalies", response_model=QualityAnomalyListResponse)
def get_anomalies(
    status: str = Query("open"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(QualityAnomaly).filter(QualityAnomaly.status == status)
    total = query.count()
    rows = query.order_by(QualityAnomaly.discovered_at.desc()).limit(limit).all()
    items = [
        QualityAnomalyItem(
            id=r.id,
            production_line=r.production_line,
            process=r.process,
            defect_type=r.defect_type,
            severity=r.severity,
            status=r.status,
            discovered_at=r.discovered_at,
            handler=r.handler,
        )
        for r in rows
    ]
    return QualityAnomalyListResponse(items=items, total=total)


@router.get("/top-defects", response_model=QualityTopDefectResponse)
def get_top_defects(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = (
        db.query(QualityDefectDetail)
        .order_by(QualityDefectDetail.quantity.desc())
        .limit(limit)
        .all()
    )
    items = [
        QualityTopDefectItem(
            rank=idx + 1,
            defect_type=r.defect_type,
            production_line=r.production_line or "-",
            process=r.process or "-",
            product_code=r.product_code,
            quantity=r.quantity,
        )
        for idx, r in enumerate(rows)
    ]
    return QualityTopDefectResponse(items=items)
