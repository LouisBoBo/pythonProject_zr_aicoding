from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import InventoryStock, User

router = APIRouter(prefix="/api/inventory-low-stock", tags=["库存低水位预警"])


class InventoryLowStockItem(BaseModel):
    id: int
    material_code: str
    material_name: str
    warehouse_name: str
    quantity: int
    safety_stock: int
    unit: str
    shortage: int = Field(description="缺口 = 安全库存 - 当前库存")
    updated_at: datetime

    model_config = {"from_attributes": True}


class InventoryLowStockListResponse(BaseModel):
    items: list[InventoryLowStockItem]
    total: int
    page: int
    size: int


@router.get(
    "",
    response_model=InventoryLowStockListResponse,
    summary="库存低水位预警列表",
    description="查询当前库存低于安全库存的物料；库存低水位预警页数据来自本接口。",
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

    items = [
        InventoryLowStockItem(
            id=row.id,
            material_code=row.material_code,
            material_name=row.material_name,
            warehouse_name=row.warehouse_name,
            quantity=row.quantity,
            safety_stock=row.safety_stock,
            unit=row.unit,
            shortage=row.safety_stock - row.quantity,
            updated_at=row.updated_at,
        )
        for row in rows
    ]
    return InventoryLowStockListResponse(items=items, total=total, page=page, size=size)
