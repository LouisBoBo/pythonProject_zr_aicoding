from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import InventoryStock, SalesOrder, ShipmentRecord, User

router = APIRouter(prefix="/api/inventory-low-stock", tags=["库存低水位预警"])


class InventoryLowStockItem(BaseModel):
    id: int
    material_code: str
    material_name: str
    warehouse_name: str
    quantity: int
    safety_stock: int
    unit: str
    shortage: int = Field(description="缺口 = 安全库存 − 现存量")
    updated_at: datetime
    # 编码与销售订单列表之间
    sales_order_in_stock: str = Field(default="", description="销售订单在库内")
    no_order_ship_page: str = Field(default="", description="无建单与发货页")
    over_ship_no_check: str = Field(default="", description="超发无校验")
    sales_order_list: str = Field(default="", description="销售订单列表（逗号分隔）")
    new_build: str = Field(default="", description="新")
    sales_order_id: int | None = Field(default=None, description="关联主销售订单 ID（登记发货用）")
    # 本项目与本项之间
    project_name: str = Field(default="", description="本项目")
    ship_register_qty: int | None = Field(default=None, description="登记发货数量（最近一次）")
    ship_register_at: datetime | None = Field(default=None, description="登记发货时间（最近一次）")
    # 本项与生产·交付达成之间
    current_item: str = Field(default="", description="本项")
    remaining_shippable: int = Field(default=0, description="剩余可发")
    order_closed: bool = Field(default=False, description="发满关单")
    p0: str = Field(default="", description="P0")
    production_delivery_rate: str = Field(default="", description="生产·交付达成")

    model_config = {"from_attributes": True}


class InventoryLowStockListResponse(BaseModel):
    items: list[InventoryLowStockItem]
    total: int
    page: int
    size: int


class RegisterShipmentBody(BaseModel):
    sales_order_id: int = Field(description="销售订单 ID")
    ship_qty: int = Field(ge=1, description="本次登记发货数量")
    shipped_at: datetime | None = Field(default=None, description="登记发货时间，默认当前时间")


def _open_sales_orders(db: Session) -> list[SalesOrder]:
    return (
        db.query(SalesOrder)
        .filter(SalesOrder.status == "open")
        .order_by(SalesOrder.order_no.asc())
        .all()
    )


def _latest_shipment_map(
    db: Session, order_ids: list[int]
) -> dict[int, ShipmentRecord]:
    if not order_ids:
        return {}
    records = (
        db.query(ShipmentRecord)
        .filter(ShipmentRecord.sales_order_id.in_(order_ids))
        .order_by(ShipmentRecord.shipped_at.desc())
        .all()
    )
    latest: dict[int, ShipmentRecord] = {}
    for rec in records:
        if rec.sales_order_id not in latest:
            latest[rec.sales_order_id] = rec
    return latest


def _delivery_rate_label(shipped: int, plan: int) -> str:
    if plan <= 0:
        return "—"
    pct = min(100, round(shipped * 100 / plan))
    return f"{pct}%"


def _build_list_item(
    row: InventoryStock,
    open_orders: list[SalesOrder],
    latest_shipments: dict[int, ShipmentRecord],
    primary_order: SalesOrder | None = None,
) -> InventoryLowStockItem:
    primary: SalesOrder | None = primary_order
    sales_order_in_stock = "否"
    no_order_ship_page = "否"
    over_ship_no_check = "否"
    sales_order_list = ""
    new_build = ""
    if open_orders:
        idx = row.material_id % len(open_orders)
        if primary is None:
            primary = open_orders[idx]
        pick = [open_orders[(idx + i) % len(open_orders)] for i in range(min(3, len(open_orders)))]
        sales_order_list = "、".join(o.order_no for o in pick)
        if primary is not None:
            new_build = f"Build-{primary.order_no.split('-')[-1]}"

    ship_register_qty: int | None = None
    ship_register_at: datetime | None = None
    remaining_shippable = 0
    order_closed = False
    production_delivery_rate = "—"
    p0 = ""
    sales_order_id: int | None = None

    if open_orders:
        sales_order_in_stock = "是" if row.quantity > 0 else "否"

    if primary is not None:
        sales_order_id = primary.id
        remaining_shippable = max(0, primary.plan_qty - primary.shipped_qty)
        order_closed = primary.status == "closed" or primary.shipped_qty >= primary.plan_qty
        if primary.shipped_qty > primary.plan_qty:
            over_ship_no_check = "是"
        production_delivery_rate = _delivery_rate_label(primary.shipped_qty, primary.plan_qty)
        last_ship = latest_shipments.get(primary.id)
        if last_ship is not None:
            ship_register_qty = last_ship.ship_qty
            ship_register_at = last_ship.shipped_at

    shortage_val = row.safety_stock - row.quantity
    p0 = "P0" if shortage_val >= max(1, row.safety_stock // 2) else ""

    project_name = row.material_name
    current_item = f"{row.quantity}{row.unit}"

    return InventoryLowStockItem(
        id=row.id,
        material_code=row.material_code,
        material_name=row.material_name,
        warehouse_name=row.warehouse_name,
        quantity=row.quantity,
        safety_stock=row.safety_stock,
        unit=row.unit,
        shortage=row.safety_stock - row.quantity,
        updated_at=row.updated_at,
        sales_order_in_stock=sales_order_in_stock,
        no_order_ship_page=no_order_ship_page,
        over_ship_no_check=over_ship_no_check,
        sales_order_list=sales_order_list,
        new_build=new_build,
        sales_order_id=sales_order_id,
        project_name=project_name,
        ship_register_qty=ship_register_qty,
        ship_register_at=ship_register_at,
        current_item=current_item,
        remaining_shippable=remaining_shippable,
        order_closed=order_closed,
        p0=p0,
        production_delivery_rate=production_delivery_rate,
    )


@router.get(
    "",
    response_model=InventoryLowStockListResponse,
    summary="库存低水位预警列表",
    description="展示当前库存低于安全库存的物料；缺口=安全库存−现存量，按缺口降序排列。",
)
def list_inventory_low_stock(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页条数"),
    warehouse_name: str | None = Query(None, description="仓库名称（模糊）"),
    keyword: str | None = Query(None, description="关键词（匹配物料编码或名称）"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(InventoryStock).filter(
        InventoryStock.safety_stock > 0,
        InventoryStock.quantity < InventoryStock.safety_stock,
    )
    if warehouse_name:
        query = query.filter(InventoryStock.warehouse_name.ilike(f"%{warehouse_name}%"))
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                InventoryStock.material_code.ilike(pattern),
                InventoryStock.material_name.ilike(pattern),
            )
        )

    shortage_expr = InventoryStock.safety_stock - InventoryStock.quantity
    query = query.order_by(shortage_expr.desc(), InventoryStock.material_code.asc())

    total = query.count()
    rows = query.offset((page - 1) * size).limit(size).all()
    open_orders = _open_sales_orders(db)
    order_ids = [o.id for o in open_orders]
    latest_shipments = _latest_shipment_map(db, order_ids)

    items = [
        _build_list_item(row, open_orders, latest_shipments)
        for row in rows
    ]
    return InventoryLowStockListResponse(items=items, total=total, page=page, size=size)


@router.post(
    "/{stock_id}/register-shipment",
    response_model=InventoryLowStockItem,
    summary="登记发货数量与时间",
    description="校验不超过剩余可发；发满后自动关单。",
)
def register_low_stock_shipment(
    stock_id: int,
    body: RegisterShipmentBody,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(InventoryStock).filter(InventoryStock.id == stock_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="低库存记录不存在")

    order = db.query(SalesOrder).filter(SalesOrder.id == body.sales_order_id).first()
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

    open_orders = _open_sales_orders(db)
    latest_shipments = _latest_shipment_map(db, [order.id])
    return _build_list_item(
        row,
        open_orders,
        latest_shipments,
        primary_order=order,
    )
