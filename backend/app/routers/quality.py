from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import SessionLocal, engine, get_db
from app.models import QualityAnomaly, QualityDefectDetail, QualityMetrics, User, WorkOrder
from app.quality_inspection_record_store import (
    TASK_STATUS_FAILED,
    TASK_STATUS_PASSED,
    TASK_STATUS_PENDING,
    QualityInspectionRecord,
    ensure_quality_inspection_records_schema,
    seed_quality_inspection_records,
)
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
from app.schemas_quality_inspection import (
    QualityInspectionRecordListResponse,
    QualityInspectionRecordResponse,
    QualityInspectionTaskListResponse,
    QualityInspectionTaskResponse,
    QualityInspectionTaskStatusUpdate,
)

router = APIRouter(prefix="/api/quality", tags=["quality"])

ensure_quality_inspection_records_schema(engine)


def _bootstrap_quality_inspection_records() -> None:
    db = SessionLocal()
    try:
        seed_quality_inspection_records(db)
    finally:
        db.close()


_bootstrap_quality_inspection_records()

TASK_STATUS_TRANSITIONS: dict[str, set[str]] = {
    TASK_STATUS_PENDING: {TASK_STATUS_PASSED, TASK_STATUS_FAILED},
    TASK_STATUS_PASSED: set(),
    TASK_STATUS_FAILED: set(),
}

LINES = ["SMT-1线", "SMT-2线", "DIP线", "组装线", "测试线"]
PROCESSES = ["贴片", "焊接", "AOI检测", "功能测试", "包装"]
DEFECT_TYPES = ["虚焊", "短路", "元件偏移", "漏件", "外观不良", "功能异常", "尺寸偏差"]


def _to_anomaly_item(row: QualityAnomaly) -> QualityAnomalyItem:
    return QualityAnomalyItem(
        id=row.id,
        production_line=row.production_line,
        process=row.process,
        defect_type=row.defect_type,
        severity=row.severity,
        status=row.status,
        discovered_at=row.discovered_at,
        handler=row.handler,
    )


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
    status: str | None = Query(None, description="异常状态：open / processing / closed，不传则不过滤"),
    page: int | None = Query(None, ge=1, description="页码（与 page_size 配合使用）"),
    page_size: int | None = Query(None, ge=1, le=100, description="每页条数"),
    limit: int = Query(20, ge=1, le=100, description="最大返回条数（未传 page 时生效，兼容看板调用）"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(QualityAnomaly)
    if status:
        query = query.filter(QualityAnomaly.status == status)
    total = query.count()
    ordered = query.order_by(QualityAnomaly.discovered_at.desc())
    if page is not None:
        effective_page_size = page_size or 10
        offset = (page - 1) * effective_page_size
        rows = ordered.offset(offset).limit(effective_page_size).all()
        return QualityAnomalyListResponse(
            items=[_to_anomaly_item(r) for r in rows],
            total=total,
            page=page,
            page_size=effective_page_size,
        )
    rows = ordered.limit(limit).all()
    return QualityAnomalyListResponse(items=[_to_anomaly_item(r) for r in rows], total=total)


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


@router.get("/inspection-records", response_model=QualityInspectionRecordListResponse)
def list_quality_inspection_records(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    inspection_no: str | None = Query(None, description="检验单号"),
    inspection_type: str | None = Query(None, description="检验类型：incoming/process/final"),
    inspection_result: str | None = Query(None, description="检验结果：pass/fail/conditional"),
    work_order_no: str | None = Query(None, description="关联工单号"),
    batch_no: str | None = Query(None, description="批次号"),
    material_code: str | None = Query(None, description="物料编码"),
    material_name: str | None = Query(None, description="物料名称"),
    inspector: str | None = Query(None, description="检验人"),
    date_from: date | None = Query(None, description="检验时间起"),
    date_to: date | None = Query(None, description="检验时间止"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """分页查询品质检验记录（不含待检任务）。"""
    query = db.query(QualityInspectionRecord).filter(
        QualityInspectionRecord.status.in_([TASK_STATUS_PASSED, TASK_STATUS_FAILED])
    )
    if inspection_no:
        query = query.filter(QualityInspectionRecord.inspection_no.ilike(f"%{inspection_no}%"))
    if inspection_type:
        query = query.filter(QualityInspectionRecord.inspection_type == inspection_type)
    if inspection_result:
        query = query.filter(QualityInspectionRecord.inspection_result == inspection_result)
    if work_order_no:
        query = query.filter(QualityInspectionRecord.work_order_no.ilike(f"%{work_order_no}%"))
    if batch_no:
        query = query.filter(QualityInspectionRecord.batch_no.ilike(f"%{batch_no}%"))
    if material_code:
        query = query.filter(QualityInspectionRecord.material_code.ilike(f"%{material_code}%"))
    if material_name:
        query = query.filter(QualityInspectionRecord.material_name.ilike(f"%{material_name}%"))
    if inspector:
        query = query.filter(QualityInspectionRecord.inspector.ilike(f"%{inspector}%"))
    if date_from:
        query = query.filter(
            QualityInspectionRecord.inspected_at >= datetime.combine(date_from, datetime.min.time())
        )
    if date_to:
        query = query.filter(
            QualityInspectionRecord.inspected_at <= datetime.combine(date_to, datetime.max.time())
        )

    total = query.count()
    rows = (
        query.order_by(QualityInspectionRecord.inspected_at.desc(), QualityInspectionRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return QualityInspectionRecordListResponse(
        items=[QualityInspectionRecordResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def _get_inspection_task_or_404(task_id: int, db: Session) -> QualityInspectionRecord:
    task = db.query(QualityInspectionRecord).filter(QualityInspectionRecord.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="检验任务不存在")
    return task


def _backfill_product_code(db: Session, row: QualityInspectionRecord) -> None:
    if row.product_code or not row.work_order_id:
        return
    wo = db.query(WorkOrder).filter(WorkOrder.id == row.work_order_id).first()
    if wo and wo.product_code:
        row.product_code = wo.product_code


@router.get("/inspection-tasks", response_model=QualityInspectionTaskListResponse)
def list_quality_inspection_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    inspection_no: str | None = Query(None, description="检验单号"),
    inspection_type: str | None = Query(None, description="检验类型：incoming/process/final"),
    status: str | None = Query(None, description="任务状态：pending/passed/failed"),
    work_order_no: str | None = Query(None, description="工单号"),
    product_code: str | None = Query(None, description="产品编码"),
    batch_no: str | None = Query(None, description="批次号"),
    material_code: str | None = Query(None, description="物料编码"),
    inspector: str | None = Query(None, description="检验人"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """分页查询检验任务。"""
    query = db.query(QualityInspectionRecord)
    if inspection_no:
        query = query.filter(QualityInspectionRecord.inspection_no.ilike(f"%{inspection_no}%"))
    if inspection_type:
        query = query.filter(QualityInspectionRecord.inspection_type == inspection_type)
    if status:
        query = query.filter(QualityInspectionRecord.status == status)
    if work_order_no:
        query = query.filter(QualityInspectionRecord.work_order_no.ilike(f"%{work_order_no}%"))
    if product_code:
        query = query.filter(QualityInspectionRecord.product_code.ilike(f"%{product_code}%"))
    if batch_no:
        query = query.filter(QualityInspectionRecord.batch_no.ilike(f"%{batch_no}%"))
    if material_code:
        query = query.filter(QualityInspectionRecord.material_code.ilike(f"%{material_code}%"))
    if inspector:
        query = query.filter(QualityInspectionRecord.inspector.ilike(f"%{inspector}%"))

    total = query.count()
    rows = (
        query.order_by(
            case((QualityInspectionRecord.status == TASK_STATUS_PENDING, 0), else_=1),
            QualityInspectionRecord.created_at.desc(),
            QualityInspectionRecord.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    for row in rows:
        _backfill_product_code(db, row)

    return QualityInspectionTaskListResponse(
        items=[QualityInspectionTaskResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/inspection-tasks/{task_id}/status", response_model=QualityInspectionTaskResponse)
def update_quality_inspection_task_status(
    task_id: int,
    payload: QualityInspectionTaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """检验任务状态流转：待检 → 合格 / 不合格。"""
    task = _get_inspection_task_or_404(task_id, db)
    allowed = TASK_STATUS_TRANSITIONS.get(task.status, set())
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"无法从 {task.status} 流转到 {payload.status}")

    task.status = payload.status
    task.inspection_result = "pass" if payload.status == TASK_STATUS_PASSED else "fail"
    if task.inspector == "待分配":
        task.inspector = current_user.username
    task.inspected_at = datetime.utcnow()
    _backfill_product_code(db, task)
    db.commit()
    db.refresh(task)
    return QualityInspectionTaskResponse.model_validate(task)
