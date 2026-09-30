"""低库存预警 API — 现存量低于安全库存的物料列表。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import InventoryStock, User

router = APIRouter(prefix="/api/inventory-low-stock", tags=["低库存预警"])


class InventoryLowStockItem(BaseModel):
    id: int
    material_code: str
    material_name: str
    warehouse_name: str
    quantity: int = Field(description="现存量")
    safety_stock: int = Field(description="安全库存")
    shortage: int = Field(description="缺口（安全库存 − 现存量）")
    unit: str
    status: str = Field(description="预警状态")
    updated_at: datetime | None = None


class InventoryLowStockListResponse(BaseModel):
    items: list[InventoryLowStockItem]
    total: int
    page: int
    page_size: int


def _alert_status(quantity: int) -> str:
    if quantity <= 0:
        return "缺货"
    return "低库存"


@router.get(
    "",
    response_model=InventoryLowStockListResponse,
    summary="低库存预警列表",
    description="查询现存量低于安全库存的物料；低库存预警页数据来自本接口，按缺口降序。",
)
def list_inventory_low_stock(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    material_code: str | None = Query(None, description="物料编码（模糊）"),
    material_name: str | None = Query(None, description="物料名称（模糊）"),
    warehouse_name: str | None = Query(None, description="仓库名称（模糊）"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shortage_expr = InventoryStock.safety_stock - InventoryStock.quantity
    query = db.query(InventoryStock).filter(
        InventoryStock.safety_stock > 0,
        InventoryStock.quantity < InventoryStock.safety_stock,
    )
    if material_code:
        query = query.filter(InventoryStock.material_code.ilike(f"%{material_code}%"))
    if material_name:
        query = query.filter(InventoryStock.material_name.ilike(f"%{material_name}%"))
    if warehouse_name:
        query = query.filter(InventoryStock.warehouse_name.ilike(f"%{warehouse_name}%"))

    total = query.count()
    rows = (
        query.order_by(shortage_expr.desc(), InventoryStock.material_code.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        InventoryLowStockItem(
            id=row.id,
            material_code=row.material_code,
            material_name=row.material_name,
            warehouse_name=row.warehouse_name,
            quantity=row.quantity,
            safety_stock=row.safety_stock,
            shortage=row.safety_stock - row.quantity,
            unit=row.unit,
            status=_alert_status(row.quantity),
            updated_at=row.updated_at,
        )
        for row in rows
    ]

    return InventoryLowStockListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
