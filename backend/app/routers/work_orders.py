from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, WorkOrder
from app.schemas import WorkOrderCreate, WorkOrderListResponse, WorkOrderResponse

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])


@router.get("", response_model=WorkOrderListResponse)
def list_work_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(WorkOrder)
    if status:
        query = query.filter(WorkOrder.status == status)
    if priority:
        query = query.filter(WorkOrder.priority == priority)
    query = query.order_by(WorkOrder.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return WorkOrderListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=WorkOrderResponse, status_code=201)
def create_work_order(
    payload: WorkOrderCreate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(WorkOrder).filter(WorkOrder.order_no == payload.order_no).first()
    if existing:
        raise HTTPException(status_code=409, detail="工单号已存在")

    work_order = WorkOrder(
        order_no=payload.order_no,
        product_name=payload.product_name,
        product_code=payload.product_code,
        production_line=payload.production_line,
        plan_quantity=payload.plan_quantity,
        priority=payload.priority,
        assignee=payload.assignee,
        start_date=payload.start_date,
        end_date=payload.end_date,
        remark=payload.remark,
    )
    db.add(work_order)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="工单号已存在") from None
    db.refresh(work_order)
    return work_order
