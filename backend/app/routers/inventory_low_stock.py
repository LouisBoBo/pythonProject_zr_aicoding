from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import InventoryStock, MaterialInbound, User

router = APIRouter(prefix="/api/inventory-low-stock", tags=["库存低水位预警"])


class InventoryLowStockItem(BaseModel):
    id: int
    material_code: str
    material_name: str
    warehouse_name: str
    last_inbound_at: datetime | None = Field(
        default=None, description="最近一次已入库单的入库时间（含年月日时）"
    )
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


def _latest_inbound_at_map(
    db: Session, stocks: list[InventoryStock]
) -> dict[tuple[int, int], datetime]:
    """按物料+仓库取最近一条已入库单的 created_at（与物料入库列表「入库时间」口径一致）。"""
    if not stocks:
        return {}
    pairs = {(s.material_id, s.warehouse_id) for s in stocks}
    material_ids = {mid for mid, _ in pairs}
    warehouse_ids = {wid for _, wid in pairs}
    candidates = (
        db.query(MaterialInbound)
        .filter(
            MaterialInbound.status == "completed",
            MaterialInbound.material_id.in_(material_ids),
            MaterialInbound.warehouse_id.in_(warehouse_ids),
        )
        .all()
    )
    latest: dict[tuple[int, int], datetime] = {}
    for inbound in candidates:
        key = (inbound.material_id, inbound.warehouse_id)
        if key not in pairs:
            continue
        prev = latest.get(key)
        if prev is None or inbound.created_at > prev:
            latest[key] = inbound.created_at
    return latest


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
    last_inbound_at_map = _latest_inbound_at_map(db, rows)

    items = [
        InventoryLowStockItem(
            id=row.id,
            material_code=row.material_code,
            material_name=row.material_name,
            warehouse_name=row.warehouse_name,
            last_inbound_at=last_inbound_at_map.get((row.material_id, row.warehouse_id)),
            quantity=row.quantity,
            safety_stock=row.safety_stock,
            unit=row.unit,
            shortage=row.safety_stock - row.quantity,
            updated_at=row.updated_at,
        )
        for row in rows
    ]
    return InventoryLowStockListResponse(items=items, total=total, page=page, size=size)
