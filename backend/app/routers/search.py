"""顶栏全局搜索 — 工单 / 设备 / 物料，关键字 ≥2，各组最多 5 条。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Equipment, Material, User, WorkOrder
from app.schemas import (
    GlobalSearchEquipmentItem,
    GlobalSearchMaterialItem,
    GlobalSearchResponse,
    GlobalSearchWorkOrderItem,
)

router = APIRouter(prefix="/api/search", tags=["search"])

LIMIT = 5


@router.get("", response_model=GlobalSearchResponse)
def global_search(
    q: str = Query("", description="关键字，至少 2 个字符"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    keyword = (q or "").strip()
    if len(keyword) < 2:
        return GlobalSearchResponse(q=keyword, work_orders=[], equipment=[], materials=[])

    like = f"%{keyword}%"

    work_orders = (
        db.query(WorkOrder)
        .filter(
            or_(
                WorkOrder.order_no.ilike(like),
                WorkOrder.product_name.ilike(like),
                WorkOrder.product_code.ilike(like),
            )
        )
        .order_by(WorkOrder.id.desc())
        .limit(LIMIT)
        .all()
    )

    equipment_rows = (
        db.query(Equipment)
        .filter(
            or_(
                Equipment.equipment_code.ilike(like),
                Equipment.name.ilike(like),
            )
        )
        .order_by(Equipment.id.desc())
        .limit(LIMIT)
        .all()
    )

    materials = (
        db.query(Material)
        .filter(
            or_(
                Material.material_code.ilike(like),
                Material.material_name.ilike(like),
            )
        )
        .order_by(Material.id.desc())
        .limit(LIMIT)
        .all()
    )

    return GlobalSearchResponse(
        q=keyword,
        work_orders=[
            GlobalSearchWorkOrderItem(
                id=wo.id,
                order_no=wo.order_no,
                product_name=wo.product_name,
                status=wo.status,
            )
            for wo in work_orders
        ],
        equipment=[
            GlobalSearchEquipmentItem(
                id=eq.id,
                equipment_code=eq.equipment_code,
                name=eq.name,
                status=eq.status,
            )
            for eq in equipment_rows
        ],
        materials=[
            GlobalSearchMaterialItem(
                id=m.id,
                material_code=m.material_code,
                material_name=m.material_name,
                category=m.category,
            )
            for m in materials
        ],
    )
