from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, WorkOrder

router = APIRouter(prefix="/api/work-order-alerts", tags=["工单逾期预警"])

EXCLUDED_STATUSES = ("completed", "cancelled")


class WorkOrderAlertItem(BaseModel):
    id: int
    order_no: str
    product_name: str
    production_line: str | None
    plan_quantity: int
    actual_quantity: int
    status: str
    priority: str
    assignee: str | None
    end_date: date
    overdue_days: int = Field(description="逾期天数（今天 - 计划结束日）")

    model_config = {"from_attributes": True}


class WorkOrderAlertListResponse(BaseModel):
    items: list[WorkOrderAlertItem]
    total: int
    page: int
    size: int


@router.get(
    "",
    response_model=WorkOrderAlertListResponse,
    summary="工单逾期预警列表",
    description="查询已过计划结束日仍未完成的工单；工单逾期预警页数据来自本接口。",
)
def list_work_order_alerts(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    production_line: str | None = Query(None, description="产线（模糊匹配）"),
    keyword: str | None = Query(None, description="关键词（匹配工单号或产品名）"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    query = db.query(WorkOrder).filter(
        WorkOrder.end_date.isnot(None),
        WorkOrder.end_date < today,
        WorkOrder.status.notin_(EXCLUDED_STATUSES),
    )
    if production_line:
        query = query.filter(WorkOrder.production_line.ilike(f"%{production_line}%"))
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            (WorkOrder.order_no.ilike(pattern)) | (WorkOrder.product_name.ilike(pattern))
        )

    query = query.order_by(WorkOrder.end_date.asc())
    total = query.count()
    rows = query.offset((page - 1) * size).limit(size).all()

    items = [
        WorkOrderAlertItem(
            id=row.id,
            order_no=row.order_no,
            product_name=row.product_name,
            production_line=row.production_line,
            plan_quantity=row.plan_quantity,
            actual_quantity=row.actual_quantity,
            status=row.status,
            priority=row.priority,
            assignee=row.assignee,
            end_date=row.end_date,
            overdue_days=(today - row.end_date).days,
        )
        for row in rows
    ]
    return WorkOrderAlertListResponse(items=items, total=total, page=page, size=size)
