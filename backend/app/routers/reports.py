from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Product,
    ProductionLine,
    ProductionOutputRecord,
    ProductionPlan,
    User,
    WorkOrder,
)
from app.schemas import (
    DailyOutputLinesResponse,
    DailyOutputReportItem,
    DailyOutputReportListResponse,
    WipReportItem,
    WipReportListResponse,
    WipReportProcessesResponse,
)
from app.work_order_utils import (
    STANDARD_PROCESSES,
    WIP_EXCLUDED_STATUSES,
    calc_wip_quantity,
    derive_current_process,
)

router = APIRouter(prefix="/api/reports", tags=["报表中心"])

WIP_METRIC = "wip"


def _to_wip_item(wo: WorkOrder) -> WipReportItem:
    process = wo.current_process or derive_current_process(
        wo.status, wo.plan_quantity, wo.actual_quantity
    )
    return WipReportItem(
        id=wo.id,
        order_no=wo.order_no,
        product_name=wo.product_name,
        current_process=process,
        wip_quantity=calc_wip_quantity(wo.plan_quantity, wo.actual_quantity),
        status=wo.status,
        start_date=wo.start_date,
        end_date=wo.end_date,
        plan_quantity=wo.plan_quantity,
        actual_quantity=wo.actual_quantity,
    )


@router.get(
    "/wip",
    response_model=WipReportListResponse,
    summary="在制品报表",
    description=(
        "按工单列出在制品数据（wip 口径：未完工且非取消的工单）。"
        "在制数量 = 计划数量 - 实际数量；工序取自 work_orders.current_process，"
        "为空时按完成进度推导（待开工为贴片）。支持按状态、工序、计划日期范围筛选。"
    ),
)
def list_wip_report(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    status: str | None = Query(None, description="工单状态筛选"),
    process: str | None = Query(None, description="工序筛选"),
    start_date: date | None = Query(None, description="计划开始日期（起）"),
    end_date: date | None = Query(None, description="计划结束日期（止）"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(WorkOrder).filter(~WorkOrder.status.in_(WIP_EXCLUDED_STATUSES))

    if status:
        query = query.filter(WorkOrder.status == status)
    if process:
        query = query.filter(WorkOrder.current_process == process)
    if start_date:
        query = query.filter(WorkOrder.start_date >= start_date)
    if end_date:
        query = query.filter(WorkOrder.end_date <= end_date)

    query = query.order_by(WorkOrder.start_date.desc(), WorkOrder.id.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    return WipReportListResponse(
        items=[_to_wip_item(wo) for wo in rows],
        total=total,
        page=page,
        page_size=page_size,
        metric=WIP_METRIC,
    )


@router.get(
    "/wip/processes",
    response_model=WipReportProcessesResponse,
    summary="在制品报表工序选项",
    description="返回标准工序列表，供报表筛选下拉使用。",
)
def list_wip_processes(
    _current_user: User = Depends(get_current_user),
):
    return WipReportProcessesResponse(processes=list(STANDARD_PROCESSES))


def _as_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])


def _build_daily_output_rows(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    production_line: str | None,
) -> list[DailyOutputReportItem]:
    """按日 / 产线 / 产品聚合产量事实与计划。"""
    day_start = datetime.combine(date_from, datetime.min.time())
    day_end = datetime.combine(date_to + timedelta(days=1), datetime.min.time())

    out_q = (
        db.query(
            func.date(ProductionOutputRecord.record_at).label("report_date"),
            ProductionOutputRecord.production_line_id,
            ProductionOutputRecord.product_id,
            func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0).label("actual_qty"),
            func.coalesce(func.sum(ProductionOutputRecord.defect_qty), 0).label("defect_qty"),
            func.coalesce(func.sum(ProductionOutputRecord.area_output), 0).label("area_output"),
        )
        .filter(
            ProductionOutputRecord.record_at >= day_start,
            ProductionOutputRecord.record_at < day_end,
        )
        .group_by(
            func.date(ProductionOutputRecord.record_at),
            ProductionOutputRecord.production_line_id,
            ProductionOutputRecord.product_id,
        )
    )
    if production_line:
        line_ids = [
            ln.id
            for ln in db.query(ProductionLine).filter(ProductionLine.name == production_line).all()
        ]
        if not line_ids:
            return []
        out_q = out_q.filter(ProductionOutputRecord.production_line_id.in_(line_ids))

    output_rows = out_q.all()

    plan_q = (
        db.query(
            ProductionPlan.plan_date,
            ProductionPlan.production_line_id,
            ProductionPlan.product_id,
            func.coalesce(func.sum(ProductionPlan.plan_qty), 0).label("plan_qty"),
        )
        .filter(
            ProductionPlan.plan_date >= date_from,
            ProductionPlan.plan_date <= date_to,
        )
        .group_by(
            ProductionPlan.plan_date,
            ProductionPlan.production_line_id,
            ProductionPlan.product_id,
        )
    )
    if production_line:
        line_ids = [
            ln.id
            for ln in db.query(ProductionLine).filter(ProductionLine.name == production_line).all()
        ]
        plan_q = plan_q.filter(ProductionPlan.production_line_id.in_(line_ids))

    plan_map: dict[tuple, int] = {}
    for row in plan_q.all():
        plan_map[(_as_date(row.plan_date), row.production_line_id, row.product_id)] = int(
            row.plan_qty or 0
        )

    line_map = {ln.id: ln.name for ln in db.query(ProductionLine).all()}
    product_map = {
        p.id: (p.product_code, p.product_name) for p in db.query(Product).all()
    }

    keys: set[tuple] = set()
    out_map: dict[tuple, tuple[int, int, float]] = {}
    for row in output_rows:
        report_date = _as_date(row.report_date)
        key = (report_date, row.production_line_id, row.product_id)
        keys.add(key)
        out_map[key] = (int(row.actual_qty or 0), int(row.defect_qty or 0), float(row.area_output or 0))

    for key in plan_map:
        keys.add(key)

    items: list[DailyOutputReportItem] = []
    for report_date, line_id, product_id in sorted(
        keys, key=lambda k: (k[0], line_map.get(k[1], ""), k[2] or 0), reverse=True
    ):
        actual_qty, defect_qty, area_output = out_map.get(
            (report_date, line_id, product_id), (0, 0, 0.0)
        )
        plan_qty = plan_map.get((report_date, line_id, product_id), 0)
        product_code, product_name = (None, None)
        if product_id and product_id in product_map:
            product_code, product_name = product_map[product_id]
        achievement = round(actual_qty / plan_qty * 100, 2) if plan_qty else 0.0
        defect_rate = (
            round(defect_qty / (actual_qty + defect_qty) * 100, 2)
            if (actual_qty + defect_qty) > 0
            else 0.0
        )
        items.append(
            DailyOutputReportItem(
                report_date=report_date,
                production_line=line_map.get(line_id, f"产线#{line_id}"),
                product_code=product_code,
                product_name=product_name,
                plan_qty=plan_qty,
                actual_qty=actual_qty,
                defect_qty=defect_qty,
                area_output=round(area_output, 2),
                achievement_rate=achievement,
                defect_rate=defect_rate,
            )
        )
    return items


@router.get(
    "/daily-output",
    response_model=DailyOutputReportListResponse,
    summary="日产报表",
    description=(
        "按生产日期、产线、产品聚合日产量："
        "实际/不良/面积来自 production_output_records，计划来自 production_plans。"
        "默认查询近 7 日（含今天）；支持按日期范围、产线筛选与分页。"
        "报表中心「日产报表」页数据来自本接口。"
    ),
)
def list_daily_output_report(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    date_from: date | None = Query(None, description="生产日期起（含）"),
    date_to: date | None = Query(None, description="生产日期止（含）"),
    production_line: str | None = Query(None, description="产线名称（精确匹配）"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    if date_to is None:
        date_to = today
    if date_from is None:
        date_from = date_to - timedelta(days=6)
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    all_items = _build_daily_output_rows(
        db,
        date_from=date_from,
        date_to=date_to,
        production_line=production_line,
    )
    total = len(all_items)
    plan_sum = sum(i.plan_qty for i in all_items)
    actual_sum = sum(i.actual_qty for i in all_items)
    defect_sum = sum(i.defect_qty for i in all_items)
    start = (page - 1) * page_size
    page_items = all_items[start : start + page_size]

    return DailyOutputReportListResponse(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
        plan_qty_sum=plan_sum,
        actual_qty_sum=actual_sum,
        defect_qty_sum=defect_sum,
    )


@router.get(
    "/daily-output/lines",
    response_model=DailyOutputLinesResponse,
    summary="日产报表产线选项",
    description="返回产线名称列表，供日产报表筛选下拉使用。",
)
def list_daily_output_lines(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lines = (
        db.query(ProductionLine.name)
        .order_by(ProductionLine.id)
        .all()
    )
    return DailyOutputLinesResponse(lines=[name for (name,) in lines])
