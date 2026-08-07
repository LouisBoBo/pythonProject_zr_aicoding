from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, WorkOrder
from app.schemas import (
    WorkOrderCreate,
    WorkOrderListResponse,
    WorkOrderResponse,
    WorkOrderStatusUpdate,
    WorkOrderUpdate,
)

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])

VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def _get_work_order_or_404(work_order_id: int, db: Session) -> WorkOrder:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    return work_order


@router.get("", response_model=WorkOrderListResponse)
def list_work_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    production_line: str | None = Query(None),
    order_no: str | None = Query(None),
    product_name: str | None = Query(None),
    search: str | None = Query(None),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(WorkOrder)
    if status:
        query = query.filter(WorkOrder.status == status)
    if priority:
        query = query.filter(WorkOrder.priority == priority)
    if production_line:
        query = query.filter(WorkOrder.production_line.ilike(f"%{production_line}%"))
    if order_no:
        query = query.filter(WorkOrder.order_no.ilike(f"%{order_no}%"))
    if product_name:
        query = query.filter(WorkOrder.product_name.ilike(f"%{product_name}%"))
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (WorkOrder.order_no.ilike(pattern))
            | (WorkOrder.product_name.ilike(pattern))
            | (WorkOrder.product_code.ilike(pattern))
        )
    query = query.order_by(WorkOrder.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return WorkOrderListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{work_order_id}", response_model=WorkOrderResponse)
def get_work_order(
    work_order_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_work_order_or_404(work_order_id, db)


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


@router.put("/{work_order_id}", response_model=WorkOrderResponse)
def update_work_order(
    work_order_id: int,
    payload: WorkOrderUpdate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    work_order = _get_work_order_or_404(work_order_id, db)
    update_data = payload.model_dump(exclude_unset=True)

    if "order_no" in update_data and update_data["order_no"] != work_order.order_no:
        duplicate = (
            db.query(WorkOrder)
            .filter(WorkOrder.order_no == update_data["order_no"], WorkOrder.id != work_order_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="工单号已存在")

    for field, value in update_data.items():
        setattr(work_order, field, value)
    work_order.updated_at = datetime.utcnow()

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="工单号已存在") from None
    db.refresh(work_order)
    return work_order


@router.patch("/{work_order_id}/status", response_model=WorkOrderResponse)
def update_work_order_status(
    work_order_id: int,
    payload: WorkOrderStatusUpdate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    work_order = _get_work_order_or_404(work_order_id, db)
    allowed = VALID_STATUS_TRANSITIONS.get(work_order.status, set())
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"无法从 {work_order.status} 流转到 {payload.status}")

    work_order.status = payload.status
    work_order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(work_order)
    return work_order


@router.delete("/{work_order_id}", status_code=204)
def delete_work_order(
    work_order_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    work_order = _get_work_order_or_404(work_order_id, db)
    db.delete(work_order)
    db.commit()
