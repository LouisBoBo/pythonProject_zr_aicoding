from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, WorkOrder
from app.schemas import WorkOrderCreate, WorkOrderListResponse, WorkOrderResponse

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])


def _generate_order_no(db: Session) -> str:
    today = date.today()
    date_str = today.strftime("%Y%m%d")
    prefix = f"WO{date_str}"
    last = (
        db.query(WorkOrder)
        .filter(WorkOrder.order_no.like(f"{prefix}%"))
        .order_by(WorkOrder.order_no.desc())
        .first()
    )
    if last:
        seq = int(last.order_no[len(prefix) :]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:03d}"


@router.get("", response_model=WorkOrderListResponse)
def list_work_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(WorkOrder).order_by(WorkOrder.created_at.desc())
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
    work_order = WorkOrder(
        order_no=_generate_order_no(db),
        product_name=payload.product_name,
        product_code=payload.product_code,
        production_line=payload.production_line,
        plan_quantity=payload.plan_quantity,
        priority=payload.priority,
        assignee=payload.assignee,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    db.add(work_order)
    db.commit()
    db.refresh(work_order)
    return work_order
