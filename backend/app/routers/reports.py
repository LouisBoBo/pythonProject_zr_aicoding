from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, WorkOrder
from app.schemas import WipReportItem, WipReportListResponse, WipReportProcessesResponse
from app.work_order_utils import (
    STANDARD_PROCESSES,
    WIP_EXCLUDED_STATUSES,
    calc_wip_quantity,
    derive_current_process,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])

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
        "为空时按完成进度推导。支持按状态、工序、计划日期范围筛选。"
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
