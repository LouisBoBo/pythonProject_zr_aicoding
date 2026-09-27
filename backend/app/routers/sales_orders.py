from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import SalesOrder, ShipmentRecord, User

router = APIRouter(prefix="/api/sales-orders", tags=["销售订单与发货"])


class SalesOrderItem(BaseModel):
    id: int
    order_no: str
    customer: str
    due_date: date
    status: str
    plan_qty: int
    shipped_qty: int
    remaining_shippable: int = Field(description="剩余可发")
    order_closed: bool = Field(description="发满关单")
    created_at: datetime

    model_config = {"from_attributes": True}


class SalesOrderListResponse(BaseModel):
    items: list[SalesOrderItem]
    total: int
    page: int
    size: int


class SalesOrderCreateBody(BaseModel):
    customer: str = Field(min_length=1, max_length=100, description="客户")
    due_date: date = Field(description="交期")
    plan_qty: int = Field(ge=1, description="计划数量")
    order_no: str | None = Field(default=None, max_length=50, description="订单号，留空自动生成")


class ShipmentRecordItem(BaseModel):
    id: int
    sales_order_id: int
    ship_qty: int
    shipped_at: datetime

    model_config = {"from_attributes": True}


class ShipmentRecordListResponse(BaseModel):
    items: list[ShipmentRecordItem]
    order_no: str


class RegisterShipmentBody(BaseModel):
    ship_qty: int = Field(ge=1, description="本次登记发货数量")
    shipped_at: datetime | None = Field(default=None, description="登记发货时间，默认当前时间")


def _order_item(order: SalesOrder) -> SalesOrderItem:
    remaining = max(0, order.plan_qty - order.shipped_qty)
    closed = order.status == "closed" or order.shipped_qty >= order.plan_qty
    return SalesOrderItem(
        id=order.id,
        order_no=order.order_no,
        customer=order.customer,
        due_date=order.due_date,
        status=order.status,
        plan_qty=order.plan_qty,
        shipped_qty=order.shipped_qty,
        remaining_shippable=remaining,
        order_closed=closed,
        created_at=order.created_at,
    )


def _generate_order_no(db: Session) -> str:
    year = date.today().year
    prefix = f"SO-{year}-"
    last = (
        db.query(SalesOrder)
        .filter(SalesOrder.order_no.like(f"{prefix}%"))
        .order_by(SalesOrder.order_no.desc())
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.order_no.split("-")[-1]) + 1
        except ValueError:
            seq = db.query(SalesOrder).count() + 1
    return f"{prefix}{seq:04d}"


@router.get(
    "",
    response_model=SalesOrderListResponse,
    summary="销售订单列表",
)
def list_sales_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    keyword: str | None = Query(None, description="订单号或客户（模糊）"),
    status: str | None = Query(None, description="状态 open / closed"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(SalesOrder)
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            or_(SalesOrder.order_no.ilike(pattern), SalesOrder.customer.ilike(pattern))
        )
    if status:
        query = query.filter(SalesOrder.status == status)
    query = query.order_by(SalesOrder.created_at.desc(), SalesOrder.id.desc())
    total = query.count()
    rows = query.offset((page - 1) * size).limit(size).all()
    return SalesOrderListResponse(
        items=[_order_item(o) for o in rows],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "",
    response_model=SalesOrderItem,
    summary="新建销售订单",
)
def create_sales_order(
    body: SalesOrderCreateBody,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order_no = (body.order_no or "").strip() or _generate_order_no(db)
    if db.query(SalesOrder).filter(SalesOrder.order_no == order_no).first():
        raise HTTPException(status_code=400, detail="订单号已存在")
    order = SalesOrder(
        order_no=order_no,
        customer=body.customer.strip(),
        due_date=body.due_date,
        status="open",
        plan_qty=body.plan_qty,
        shipped_qty=0,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return _order_item(order)


@router.get(
    "/{order_id}/shipments",
    response_model=ShipmentRecordListResponse,
    summary="订单发货记录",
)
def list_order_shipments(
    order_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="销售订单不存在")
    records = (
        db.query(ShipmentRecord)
        .filter(ShipmentRecord.sales_order_id == order_id)
        .order_by(ShipmentRecord.shipped_at.desc(), ShipmentRecord.id.desc())
        .all()
    )
    return ShipmentRecordListResponse(
        items=[ShipmentRecordItem.model_validate(r) for r in records],
        order_no=order.order_no,
    )


@router.post(
    "/{order_id}/register-shipment",
    response_model=SalesOrderItem,
    summary="登记发货数量与时间",
    description="校验不超过剩余可发；发满后自动关单。",
)
def register_sales_order_shipment(
    order_id: int,
    body: RegisterShipmentBody,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="销售订单不存在")
    if order.status == "closed":
        raise HTTPException(status_code=400, detail="订单已关单，无法继续登记发货")

    remaining = max(0, order.plan_qty - order.shipped_qty)
    if body.ship_qty > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"登记发货数量不能超过剩余可发（{remaining}）",
        )

    shipped_at = body.shipped_at or datetime.utcnow()
    db.add(
        ShipmentRecord(
            sales_order_id=order.id,
            ship_qty=body.ship_qty,
            shipped_at=shipped_at,
        )
    )
    order.shipped_qty += body.ship_qty
    if order.shipped_qty >= order.plan_qty:
        order.status = "closed"

    db.commit()
    db.refresh(order)
    return _order_item(order)
